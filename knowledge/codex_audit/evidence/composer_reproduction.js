// Synthetische fixture; geen browser- of netwerkactie.
const fs = require('fs');
const src = fs.readFileSync('control/tampermonkey_multichat/prediction-chat-wake.user.js', 'utf8');
const fn = src.slice(src.indexOf('  async function submitMessage('), src.indexOf('  async function ack('));
let composer = {value: 'UNSENT USER DRAFT'}, sent = [];
const chatIsBusy = () => false, findComposer = () => composer, status = () => {}, sleep = async () => {};
const setComposerText = (el, text) => el.value = text;
const findSendButton = () => ({click: () => {sent.push(composer.value); composer.value = '';}});
eval(fn + '; submitMessage("SYNTHETIC BRIDGE MESSAGE").then(result => console.log(JSON.stringify({synthetic_only:true, initial_draft:"UNSENT USER DRAFT", sent, remaining:composer.value, reported_success:result})))');
