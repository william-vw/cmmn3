// const { JSDOM } = require("jsdom");
// const dom = new JSDOM(`<!DOCTYPE html><p id="main">Hello world</p>`);
// console.log(dom.window.document.querySelector("#main").textContent); // Outputs "Hello world"
// const dom = new JSDOM(`<!DOCTYPE html><div id="canvas"></div>`);
// window = dom.window
// document = dom.window.document
// Element = window.Element

import puppeteer from 'puppeteer';
import { resolve } from 'path';
import fs from 'fs';

const viewerPath = process.argv[2];
const imgPath = process.argv[3];

const browser = await puppeteer.launch();
const page = await browser.newPage();
page.on('console', message => console.log(message.type().toUpperCase(), ":", message.text()))
    .on('pageerror', ({ message }) => console.log("ERROR", ":", message))
    // .on('request', request =>
    //     console.log(request))
    // .on('response', response =>
    //     console.log(`${response.status()} ${response.url()}`))
    // .on('requestfailed', request =>
    //     console.log(`${request.failure().errorText} ${request.url()}`))

await page.goto(`file://${resolve(viewerPath)}`);

await page.setViewport({ width: 1920, height: 1080, deviceScaleFactor: 2 });

const element = await page.$("#canvas .djs-container > svg > g");
await element.screenshot({
    path: imgPath,
    type: 'png',
});

await browser.close();


// const CmmnViewer = require('./cmmn.js');
// // var CmmnViewer = require('cmmn-js');

// var viewer = new CmmnViewer({
//   container: '#canvas'
// });

// let url = "./cap-all.cmmn"
// let xml = fs.readFileSync(url, { encoding: 'utf8', flag: 'r' })
// // console.log(xml)

// viewer.importXML(xml, function(err) {
//   if (!err) {
//     console.log('success!');
//     // viewer.get('canvas').zoom('fit-viewport');
//   } else {
//     console.log('something went wrong:', err);
//   }
// });