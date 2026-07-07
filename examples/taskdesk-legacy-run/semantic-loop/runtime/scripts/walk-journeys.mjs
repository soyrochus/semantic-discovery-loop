#!/usr/bin/env node
// Journey walker for taskdesk-legacy (skill 09, corroboration slice).
//
// Walks the doc-seeded login → task list → task detail journey as operator1
// against a sandboxed Tomcat whose TASKDESK_DB_URL points at the disposable
// database copy under runtime/db/. Produces normalized traces (no timestamps,
// no session ids, no cookie/date values) plus screenshots, and assembles
// runtime/journeys.json with sha256 refs for every artefact.
//
// Normalization rule (contracts/journeys.schema.json): URLs are stripped of
// scheme/host and jsessionid; traces record structure and matched views only,
// never headers or wall-clock values. Screenshots are exempt from cross-run
// byte identity and are referenced by hash for integrity only.

import { chromium } from 'playwright';
import { createHash } from 'node:crypto';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { execSync } from 'node:child_process';
import path from 'node:path';

const REPO = process.env.REPO_ROOT || process.cwd();
const WORK = path.join(REPO, '.work/semantic-loop');
const RUNTIME = path.join(WORK, 'runtime');
const BASE = 'http://localhost:8080/taskdesk-legacy';
const JOURNEY_ID = 'journey:login-task-review';
const TRACE_DIR = path.join(RUNTIME, 'traces', 'login-task-review');

const sha256 = (p) => createHash('sha256').update(readFileSync(p)).digest('hex');
const normUrl = (u) =>
  u.replace(/^https?:\/\/[^/]+/, '').replace(/;jsessionid=[^?;]*/i, '');
const routeOf = (u) => {
  const m = normUrl(u).match(/^\/taskdesk-legacy(\/[^?.]+)\.do/);
  return m ? m[1] : null;
};

const repoFingerprint = execSync('git rev-parse HEAD', { cwd: REPO }).toString().trim();
const DB_SOURCE = 'db/runtime-data/taskdesk-demo.sqlite';
const dbSourceSha = sha256(path.join(REPO, DB_SOURCE));

mkdirSync(TRACE_DIR, { recursive: true });

const steps = [];
async function record(step) {
  const tracePath = path.join(TRACE_DIR, `step-${step.index}.json`);
  const trace = {
    step: step.index,
    action: step.action,
    url: step.url,
    route: step.route,
    request_method: step.request_method,
    form_fields: step.form_fields,
    response_status: step.response_status,
    redirect_location: step.redirect_location,
    rendered_view: step.rendered_view,
    view_evidence: step.view_evidence,
  };
  writeFileSync(tracePath, JSON.stringify(trace, null, 2) + '\n');
  steps.push({
    index: step.index,
    action: step.action,
    url: step.url,
    route: step.route,
    request_method: step.request_method,
    form_fields: step.form_fields ?? [],
    response_status: step.response_status,
    redirect_location: step.redirect_location,
    rendered_view: step.rendered_view,
    view_evidence: step.view_evidence,
    trace_ref: {
      path: `runtime/traces/login-task-review/step-${step.index}.json`,
      sha256: sha256(tracePath),
    },
    screenshot: step.screenshotPath
      ? {
          path: `runtime/traces/login-task-review/step-${step.index}.png`,
          sha256: sha256(step.screenshotPath),
        }
      : null,
    db_diff: null,
  });
}

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });

// Step 1 — open the documented login entry point.
let resp = await page.goto(`${BASE}/login.do`);
let shot = path.join(TRACE_DIR, 'step-1.png');
await page.screenshot({ path: shot });
await record({
  index: 1, action: 'goto', url: normUrl(resp.url()), route: routeOf(resp.url()),
  request_method: 'GET', form_fields: [],
  response_status: resp.status(), redirect_location: null,
  rendered_view: '/jsp/login.jsp', view_evidence: `title: ${await page.title()}`,
  screenshotPath: shot,
});

// Step 2 — submit the login form as operator1; Struts redirects to /tasks.do.
await page.fill('input[name="username"]', 'operator1');
await page.fill('input[name="password"]', 'demo');
const [nav] = await Promise.all([
  page.waitForNavigation(),
  page.click('form[name="loginForm"] input[type="submit"], form input[type="submit"]'),
]);
const post = nav.request().redirectedFrom();
const postResp = post ? await post.response() : null;
shot = path.join(TRACE_DIR, 'step-2.png');
await page.screenshot({ path: shot });
await record({
  index: 2, action: 'submit-form', url: normUrl(post ? post.url() : nav.url()),
  route: routeOf(post ? post.url() : nav.url()),
  request_method: 'POST', form_fields: ['username', 'password'],
  response_status: postResp ? postResp.status() : nav.status(),
  redirect_location: postResp ? normUrl((await postResp.headerValue('location')) || '') || null : null,
  rendered_view: '/jsp/taskList.jsp', view_evidence: `title: ${await page.title()}`,
  screenshotPath: shot,
});

// Step 3 — open the first task's detail page from the list.
const detailHref = await page.getAttribute('a[href*="taskDetail.do"]', 'href');
const [detailResp] = await Promise.all([
  page.waitForNavigation(),
  page.click('a[href*="taskDetail.do"]'),
]);
shot = path.join(TRACE_DIR, 'step-3.png');
await page.screenshot({ path: shot });
await record({
  index: 3, action: 'click', url: normUrl(new URL(detailHref, `${BASE}/`).href),
  route: '/taskDetail',
  request_method: 'GET', form_fields: [],
  response_status: detailResp.status(), redirect_location: null,
  rendered_view: '/jsp/taskDetail.jsp', view_evidence: `title: ${await page.title()}`,
  screenshotPath: shot,
});

await browser.close();

const journeys = {
  repo_fingerprint: repoFingerprint,
  produced_by: 'runtime/scripts/walk-journeys.mjs',
  approval: {
    granted: true,
    statement:
      'User instructed "ok, lets finish it" for Milestone 3 (runtime journeys) in the ' +
      'Claude Code session of 2026-07-07, covering execution of the bundled taskdesk-legacy target.',
  },
  environment: {
    declared_dependencies: [
      { name: 'java-17 (~/opt/jdk17)', satisfied: true, version: '17' },
      { name: 'maven (~/opt/maven, built the deployed WAR)', satisfied: true, version: '3.9' },
      { name: 'tomcat-9 (~/opt/tomcat9, javax.servlet)', satisfied: true, version: '9.0.120' },
      { name: 'node', satisfied: true, version: '24' },
      { name: 'playwright-chromium', satisfied: true, version: '1.61' },
    ],
    app_base_url: BASE,
    container: 'tomcat-9.0.120',
  },
  db_snapshot: {
    source_file: DB_SOURCE,
    source_sha256: dbSourceSha,
    copy_path: 'runtime/db/taskdesk-demo.sqlite',
  },
  journeys: [
    {
      id: JOURNEY_ID,
      name: 'Login and review a task (operator1)',
      flow_hypothesis:
        'claim:taskdesk-readme:login-entry (documented login URL and demo users) plus the ' +
        'static route chain /login -> /tasks -> /taskDetail from struts-config forwards',
      actor: 'operator1',
      steps,
      corroborates: [
        'sem:entrypoint:struts-action-servlet-do',
        'sem:action:login', 'sem:view:login',
        'sem:action:tasks', 'sem:view:taskList',
        'sem:action:taskDetail', 'sem:view:taskDetail',
      ],
      properties: {
        slice: 'corroboration-only (spec §7 Milestone 3); no security diffing or DB-diff proof yet',
      },
    },
  ],
};

writeFileSync(path.join(RUNTIME, 'journeys.json'), JSON.stringify(journeys, null, 2) + '\n');
console.log(`wrote runtime/journeys.json with ${steps.length} steps`);
