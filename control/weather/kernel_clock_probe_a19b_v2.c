/* A19B-v2 read-only kernel clock evidence probe.
 *
 * Calls adjtimex() with modes=0. This reads Linux kernel NTP discipline state
 * and does not request any clock modification.
 */
#define _GNU_SOURCE
#include <errno.h>
#include <stdio.h>
#include <string.h>
#include <sys/timex.h>

static const char *state_name(int state)
{
    switch (state) {
        case TIME_OK: return "TIME_OK";
        case TIME_INS: return "TIME_INS";
        case TIME_DEL: return "TIME_DEL";
        case TIME_OOP: return "TIME_OOP";
        case TIME_WAIT: return "TIME_WAIT";
        case TIME_ERROR: return "TIME_ERROR";
        default: return "TIME_UNKNOWN";
    }
}

int main(void)
{
    struct timex tx;
    memset(&tx, 0, sizeof(tx));
    tx.modes = 0;

    errno = 0;
    int state = adjtimex(&tx);
    if (state < 0) {
        fprintf(stderr, "adjtimex read failed: errno=%d %s\n", errno, strerror(errno));
        return 2;
    }

    const int nano = (tx.status & STA_NANO) != 0;
    const double offset_ms = nano ? ((double)tx.offset / 1000000.0)
                                  : ((double)tx.offset / 1000.0);
    const double maxerror_ms = (double)tx.maxerror / 1000.0;
    const double esterror_ms = (double)tx.esterror / 1000.0;

    printf("{");
    printf("\"schema\":\"A19B_KERNEL_CLOCK_PROBE_V1\",");
    printf("\"read_only_modes\":%u,", tx.modes);
    printf("\"time_state\":%d,", state);
    printf("\"time_state_name\":\"%s\",", state_name(state));
    printf("\"status_raw\":%d,", tx.status);
    printf("\"sta_unsync\":%s,", (tx.status & STA_UNSYNC) ? "true" : "false");
    printf("\"sta_clockerr\":%s,", (tx.status & STA_CLOCKERR) ? "true" : "false");
    printf("\"sta_nano\":%s,", nano ? "true" : "false");
    printf("\"offset_raw\":%ld,", tx.offset);
    printf("\"offset_unit\":\"%s\",", nano ? "nanoseconds" : "microseconds");
    printf("\"offset_ms\":%.9f,", offset_ms);
    printf("\"maxerror_us\":%ld,", tx.maxerror);
    printf("\"maxerror_ms\":%.9f,", maxerror_ms);
    printf("\"esterror_us\":%ld,", tx.esterror);
    printf("\"esterror_ms\":%.9f,", esterror_ms);
    printf("\"precision_us\":%ld,", tx.precision);
    printf("\"tai\":%d,", tx.tai);
    printf("\"kernel_time_sec\":%ld,", (long)tx.time.tv_sec);
    printf("\"kernel_time_subsec\":%ld", (long)tx.time.tv_usec);
    printf("}\n");
    return 0;
}
