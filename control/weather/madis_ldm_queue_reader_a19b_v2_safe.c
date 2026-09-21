/*
 * A19B-v2 safe read-only LDM product-queue reader.
 *
 * Uses only pq_next() callback fields whose semantics/initialization are
 * evidenced in current Unidata LDM source. In particular, it deliberately
 * does NOT read queue_par_t.is_locked because current pq_next() source does
 * not provide sufficient initialization evidence for that field.
 */
#define _POSIX_C_SOURCE 200809L

#include "pq.h"

#include <errno.h>
#include <regex.h>
#include <signal.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/time.h>
#include <time.h>

static const unsigned char FRAME_MAGIC[8] = {'A','1','9','B','Q','V','2','\0'};
static const uint32_t FRAME_VERSION = 1;
static const size_t MAX_TEXT_BYTES = 16u * 1024u;

enum {
    FLAG_EARLY_CURSOR = 1u << 0,
    FLAG_QUEUE_FULL = 1u << 1,
};

typedef struct {
    regex_t pattern;
    bool pattern_ready;
    bool once;
    bool emitted;
    bool write_error;
    timestampt start_at;
} reader_state;

static volatile sig_atomic_t stop_requested = 0;

static void on_stop(int sig)
{
    (void)sig;
    stop_requested = 1;
}

static bool timeval_before(const timestampt *a, const timestampt *b)
{
    return a->tv_sec < b->tv_sec ||
           (a->tv_sec == b->tv_sec && a->tv_usec < b->tv_usec);
}

static bool write_all(const void *data, size_t len)
{
    const unsigned char *p = (const unsigned char *)data;
    while (len > 0) {
        size_t n = fwrite(p, 1, len, stdout);
        if (n == 0) {
            return false;
        }
        p += n;
        len -= n;
    }
    return true;
}

static bool write_u32_be(uint32_t value)
{
    unsigned char b[4] = {
        (unsigned char)((value >> 24) & 0xffu),
        (unsigned char)((value >> 16) & 0xffu),
        (unsigned char)((value >> 8) & 0xffu),
        (unsigned char)(value & 0xffu),
    };
    return write_all(b, sizeof(b));
}

static bool write_i32_be(int32_t value)
{
    return write_u32_be((uint32_t)value);
}

static bool write_u64_be(uint64_t value)
{
    unsigned char b[8] = {
        (unsigned char)((value >> 56) & 0xffu),
        (unsigned char)((value >> 48) & 0xffu),
        (unsigned char)((value >> 40) & 0xffu),
        (unsigned char)((value >> 32) & 0xffu),
        (unsigned char)((value >> 24) & 0xffu),
        (unsigned char)((value >> 16) & 0xffu),
        (unsigned char)((value >> 8) & 0xffu),
        (unsigned char)(value & 0xffu),
    };
    return write_all(b, sizeof(b));
}

static bool write_i64_be(int64_t value)
{
    return write_u64_be((uint64_t)value);
}

static bool emit_frame(
        const prod_par_t *prod_par,
        const queue_par_t *queue_par,
        reader_state *state)
{
    const prod_info *info = &prod_par->info;
    const char *ident = info->ident ? info->ident : "";
    const char *origin = info->origin ? info->origin : "";
    size_t ident_len = strlen(ident);
    size_t origin_len = strlen(origin);
    size_t payload_len = (size_t)info->sz;

    if (ident_len > MAX_TEXT_BYTES || origin_len > MAX_TEXT_BYTES) {
        fprintf(stderr, "A19B-v2 metadata string too large; refusing product\n");
        return false;
    }
    if (prod_par->data == NULL && payload_len != 0) {
        fprintf(stderr, "A19B-v2 null decoded product data\n");
        return false;
    }

    struct timespec callback_rt;
    struct timespec callback_mono;
    if (clock_gettime(CLOCK_REALTIME, &callback_rt) != 0 ||
            clock_gettime(CLOCK_MONOTONIC, &callback_mono) != 0) {
        fprintf(stderr, "A19B-v2 clock_gettime failed: %s\n", strerror(errno));
        return false;
    }

    uint32_t flags = 0;
    if (queue_par->early_cursor) {
        flags |= FLAG_EARLY_CURSOR;
    }
    if (queue_par->is_full) {
        flags |= FLAG_QUEUE_FULL;
    }

    bool ok = true;
    ok = ok && write_all(FRAME_MAGIC, sizeof(FRAME_MAGIC));
    ok = ok && write_u32_be(FRAME_VERSION);
    ok = ok && write_u32_be(flags);
    ok = ok && write_u64_be((uint64_t)payload_len);
    ok = ok && write_i64_be((int64_t)queue_par->inserted.tv_sec);
    ok = ok && write_i32_be((int32_t)queue_par->inserted.tv_usec);
    ok = ok && write_i64_be((int64_t)info->arrival.tv_sec);
    ok = ok && write_i32_be((int32_t)info->arrival.tv_usec);
    ok = ok && write_i64_be((int64_t)callback_rt.tv_sec);
    ok = ok && write_i32_be((int32_t)callback_rt.tv_nsec);
    ok = ok && write_i64_be((int64_t)callback_mono.tv_sec);
    ok = ok && write_i32_be((int32_t)callback_mono.tv_nsec);
    ok = ok && write_u32_be((uint32_t)info->feedtype);
    ok = ok && write_u32_be((uint32_t)info->seqno);
    ok = ok && write_u32_be((uint32_t)info->sz);
    ok = ok && write_u32_be((uint32_t)ident_len);
    ok = ok && write_u32_be((uint32_t)origin_len);
    ok = ok && write_all(info->signature, sizeof(info->signature));
    ok = ok && write_all(ident, ident_len);
    ok = ok && write_all(origin, origin_len);
    ok = ok && write_all(prod_par->data, payload_len);

    if (!ok || fflush(stdout) != 0) {
        fprintf(stderr, "A19B-v2 stdout frame write failed\n");
        state->write_error = true;
        return false;
    }

    state->emitted = true;
    return true;
}

static void on_product(
        const prod_par_t *restrict prod_par,
        const queue_par_t *restrict queue_par,
        void *restrict app_par)
{
    reader_state *state = (reader_state *)app_par;
    if (stop_requested || state->write_error) {
        return;
    }

    if (timeval_before(&queue_par->inserted, &state->start_at)) {
        return;
    }

    const char *ident = prod_par->info.ident ? prod_par->info.ident : "";
    if (regexec(&state->pattern, ident, 0, NULL, 0) != 0) {
        return;
    }

    (void)emit_frame(prod_par, queue_par, state);
}

static void usage(const char *prog)
{
    fprintf(stderr, "usage: %s QUEUE_PATH PRODUCT_ID_ERE [--once]\n", prog);
}

int main(int argc, char **argv)
{
    if (argc < 3 || argc > 4) {
        usage(argv[0]);
        return 2;
    }

    bool once = false;
    if (argc == 4) {
        if (strcmp(argv[3], "--once") != 0) {
            usage(argv[0]);
            return 2;
        }
        once = true;
    }

    reader_state state;
    memset(&state, 0, sizeof(state));
    state.once = once;

    int rstatus = regcomp(&state.pattern, argv[2], REG_EXTENDED | REG_NOSUB);
    if (rstatus != 0) {
        char msg[256];
        regerror(rstatus, &state.pattern, msg, sizeof(msg));
        fprintf(stderr, "A19B-v2 invalid product identifier regex: %s\n", msg);
        return 3;
    }
    state.pattern_ready = true;

    struct sigaction sa;
    memset(&sa, 0, sizeof(sa));
    sa.sa_handler = on_stop;
    sigemptyset(&sa.sa_mask);
    (void)sigaction(SIGTERM, &sa, NULL);
    (void)sigaction(SIGINT, &sa, NULL);

    pqueue *queue = NULL;
    int status = pq_open(argv[1], PQ_READONLY, &queue);
    if (status != 0 || queue == NULL) {
        fprintf(stderr, "A19B-v2 pq_open failed: status=%d queue=%s\n", status, argv[1]);
        regfree(&state.pattern);
        return 4;
    }

    if (gettimeofday(&state.start_at, NULL) != 0) {
        fprintf(stderr, "A19B-v2 gettimeofday failed: %s\n", strerror(errno));
        (void)pq_close(queue);
        regfree(&state.pattern);
        return 5;
    }

    timestampt cursor = state.start_at;
    if (cursor.tv_sec > 0) {
        cursor.tv_sec -= 1;
    }
    pq_cset(queue, &cursor);

    int exit_code = 0;
    while (!stop_requested) {
        state.emitted = false;
        status = pq_next(queue, false, PQ_CLASS_ALL, on_product, false, &state);

        if (state.write_error) {
            exit_code = 6;
            break;
        }
        if (state.once && state.emitted) {
            break;
        }
        if (status == PQ_END) {
            (void)pq_suspend(1);
            continue;
        }
        if (status != 0) {
            fprintf(stderr, "A19B-v2 pq_next failed: status=%d\n", status);
            exit_code = 7;
            break;
        }
    }

    int close_status = pq_close(queue);
    if (close_status != 0 && exit_code == 0) {
        fprintf(stderr, "A19B-v2 pq_close failed: status=%d\n", close_status);
        exit_code = 8;
    }
    if (state.pattern_ready) {
        regfree(&state.pattern);
    }
    return exit_code;
}
