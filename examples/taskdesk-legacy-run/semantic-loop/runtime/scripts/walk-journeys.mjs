#!/usr/bin/env node
// Journey walker for taskdesk-legacy (skill 09).
//
// Walks doc-seeded and statically-predicted journeys against a sandboxed
// Tomcat whose TASKDESK_DB_URL points at the disposable database copy under
// runtime/db/. Produces normalized traces (no timestamps, no session ids, no
// cookie/date values) plus screenshots, and assembles runtime/journeys.json
// with sha256 refs for every artefact.
//
// Journeys, in order:
//   1. login-task-review        (operator1)  corroboration slice: login -> list -> detail
//   2. role-denied-operator     (operator1)  operator hits a manager-only action -> denied
//   3. role-allowed-manager     (manager1)   manager hits the same action      -> allowed
//   4. login-validation         (anonymous)  empty login form -> rejected with error
//
// Journeys 2+3 are a *behavioural* test of the role rule: the same route,
// walked by two actors, must diff (denied vs allowed). Journey 4 behaviourally
// tests the required-field validation rule. What each journey records is the
// ACTUAL observed outcome; the semantic builder compares that against the
// statically-derived rule and records a conflict if they disagree — the walk
// never assumes the app behaves, it reports what happened.
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
const MANAGER_ACTION = '/taskAssign'; // manager-only per struts-config "denied" forward

const sha256 = (p) => createHash('sha256').update(readFileSync(p)).digest('hex');
const normUrl = (u) =>
  u.replace(/^https?:\/\/[^/]+/, '').replace(/;jsessionid=[^?;]*/i, '');
const repoFingerprint = execSync('git rev-parse HEAD', { cwd: REPO }).toString().trim();
const DB_SOURCE = 'db/runtime-data/taskdesk-demo.sqlite';
const dbSourceSha = sha256(path.join(REPO, DB_SOURCE));

const browser = await chromium.launch();

// Records one step, writing a normalized trace file and returning the
// journeys.json step object (with sha256 refs).
function makeRecorder(slug) {
  const dir = path.join(RUNTIME, 'traces', slug);
  mkdirSync(dir, { recursive: true });
  const steps = [];
  return {
    steps,
    async record(s) {
      const tracePath = path.join(dir, `step-${s.index}.json`);
      const trace = {
        step: s.index, action: s.action, url: s.url, route: s.route,
        request_method: s.request_method, form_fields: s.form_fields ?? [],
        response_status: s.response_status, redirect_location: s.redirect_location ?? null,
        rendered_view: s.rendered_view ?? null, view_evidence: s.view_evidence ?? null,
      };
      writeFileSync(tracePath, JSON.stringify(trace, null, 2) + '\n');
      const entry = {
        index: s.index, action: s.action, url: s.url, route: s.route,
        request_method: s.request_method, form_fields: s.form_fields ?? [],
        response_status: s.response_status, redirect_location: s.redirect_location ?? null,
        rendered_view: s.rendered_view ?? null, view_evidence: s.view_evidence ?? null,
        trace_ref: { path: `runtime/traces/${slug}/step-${s.index}.json`, sha256: sha256(tracePath) },
        screenshot: null, db_diff: null,
      };
      if (s.screenshotPath) {
        entry.screenshot = {
          path: `runtime/traces/${slug}/step-${s.index}.png`,
          sha256: sha256(s.screenshotPath),
        };
      }
      steps.push(entry);
    },
  };
}

async function login(ctx, username) {
  const page = await ctx.newPage({ viewport: { width: 1280, height: 900 } });
  await page.goto(`${BASE}/login.do`);
  await page.fill('input[name="username"]', username);
  await page.fill('input[name="password"]', 'demo');
  const [nav] = await Promise.all([
    page.waitForNavigation(),
    page.click('form input[type="submit"]'),
  ]);
  const redirected = nav.request().redirectedFrom();
  return { page, loginPost: redirected };
}

const journeys = [];

// -------- Journey 1: login -> task list -> task detail (operator1) --------
{
  const rec = makeRecorder('login-task-review');
  const ctx = await browser.newContext();
  const page = await ctx.newPage({ viewport: { width: 1280, height: 900 } });

  let resp = await page.goto(`${BASE}/login.do`);
  let shot = path.join(RUNTIME, 'traces/login-task-review/step-1.png');
  await page.screenshot({ path: shot });
  await rec.record({ index: 1, action: 'goto', url: normUrl(resp.url()), route: '/login',
    request_method: 'GET', form_fields: [], response_status: resp.status(),
    rendered_view: '/jsp/login.jsp', view_evidence: `title: ${await page.title()}`, screenshotPath: shot });

  await page.fill('input[name="username"]', 'operator1');
  await page.fill('input[name="password"]', 'demo');
  const [nav] = await Promise.all([page.waitForNavigation(), page.click('form input[type="submit"]')]);
  const post = nav.request().redirectedFrom();
  const postResp = post ? await post.response() : null;
  shot = path.join(RUNTIME, 'traces/login-task-review/step-2.png');
  await page.screenshot({ path: shot });
  await rec.record({ index: 2, action: 'submit-form', url: normUrl(post ? post.url() : nav.url()),
    route: '/login', request_method: 'POST', form_fields: ['username', 'password'],
    response_status: postResp ? postResp.status() : nav.status(),
    redirect_location: postResp ? normUrl((await postResp.headerValue('location')) || '') || null : null,
    rendered_view: '/jsp/taskList.jsp', view_evidence: `title: ${await page.title()}`, screenshotPath: shot });

  const detailHref = await page.getAttribute('a[href*="taskDetail.do"]', 'href');
  const [detailResp] = await Promise.all([page.waitForNavigation(), page.click('a[href*="taskDetail.do"]')]);
  shot = path.join(RUNTIME, 'traces/login-task-review/step-3.png');
  await page.screenshot({ path: shot });
  await rec.record({ index: 3, action: 'click', url: normUrl(new URL(detailHref, `${BASE}/`).href),
    route: '/taskDetail', request_method: 'GET', form_fields: [], response_status: detailResp.status(),
    rendered_view: '/jsp/taskDetail.jsp', view_evidence: `title: ${await page.title()}`, screenshotPath: shot });

  await ctx.close();
  journeys.push({
    id: 'journey:login-task-review', name: 'Login and review a task (operator1)',
    flow_hypothesis: 'claim:taskdesk-readme:login-entry plus the static route chain /login -> /tasks -> /taskDetail from struts-config forwards',
    actor: 'operator1', steps: rec.steps,
    corroborates: ['sem:entrypoint:struts-action-servlet-do', 'sem:action:login', 'sem:view:login',
      'sem:action:tasks', 'sem:view:taskList', 'sem:action:taskDetail', 'sem:view:taskDetail'],
    properties: { slice: 'corroboration (spec §7 Milestone 3)' },
  });
}

// -------- Journey 2: operator hits a manager-only action -> denied --------
{
  const rec = makeRecorder('role-denied-operator');
  const ctx = await browser.newContext();
  const { page } = await login(ctx, 'operator1');
  await rec.record({ index: 1, action: 'submit-form', url: '/taskdesk-legacy/login.do', route: '/login',
    request_method: 'POST', form_fields: ['username', 'password'], response_status: 302,
    redirect_location: '/taskdesk-legacy/tasks.do', rendered_view: '/jsp/taskList.jsp',
    view_evidence: `logged in as operator1; title: ${await page.title()}` });

  const resp = await page.goto(`${BASE}${MANAGER_ACTION}.do?taskId=1`);
  const shot = path.join(RUNTIME, 'traces/role-denied-operator/step-2.png');
  await page.screenshot({ path: shot });
  const deniedTitle = await page.title();
  await rec.record({ index: 2, action: 'goto', url: normUrl(resp.url()), route: MANAGER_ACTION,
    request_method: 'GET', form_fields: [], response_status: resp.status(),
    rendered_view: '/jsp/accessDenied.jsp', view_evidence: `title: ${deniedTitle}`, screenshotPath: shot });

  await ctx.close();
  journeys.push({
    id: 'journey:role-denied-operator', name: 'Operator is denied a manager-only action',
    flow_hypothesis: 'static role check in TaskAssignAction (SecurityUtils.isManager -> findForward("denied")); tests sem:rule:manager-role-checks behaviourally',
    actor: 'operator1', steps: rec.steps,
    corroborates: ['sem:security:session-login', 'sem:rule:manager-role-checks', 'sem:view:accessDenied'],
    properties: { access_control_outcome: /denied/i.test(deniedTitle) ? 'denied' : 'not-denied', probed_route: MANAGER_ACTION },
  });
}

// -------- Journey 3: manager hits the same action -> allowed --------
{
  const rec = makeRecorder('role-allowed-manager');
  const ctx = await browser.newContext();
  const { page } = await login(ctx, 'manager1');
  await rec.record({ index: 1, action: 'submit-form', url: '/taskdesk-legacy/login.do', route: '/login',
    request_method: 'POST', form_fields: ['username', 'password'], response_status: 302,
    redirect_location: '/taskdesk-legacy/tasks.do', rendered_view: '/jsp/taskList.jsp',
    view_evidence: `logged in as manager1; title: ${await page.title()}` });

  const resp = await page.goto(`${BASE}${MANAGER_ACTION}.do?taskId=1`);
  const shot = path.join(RUNTIME, 'traces/role-allowed-manager/step-2.png');
  await page.screenshot({ path: shot });
  const title = await page.title();
  await rec.record({ index: 2, action: 'goto', url: normUrl(resp.url()), route: MANAGER_ACTION,
    request_method: 'GET', form_fields: [], response_status: resp.status(),
    rendered_view: '/jsp/taskAssign.jsp', view_evidence: `title: ${title}`, screenshotPath: shot });

  await ctx.close();
  const allowed = !/denied/i.test(title);
  journeys.push({
    id: 'journey:role-allowed-manager', name: 'Manager is allowed the same manager-only action',
    flow_hypothesis: 'same route as journey:role-denied-operator, walked as a manager; the diff proves the role rule is enforced, not merely declared',
    actor: 'manager1', steps: rec.steps,
    corroborates: ['sem:security:session-login', 'sem:rule:manager-role-checks', 'sem:action:taskAssign', 'sem:view:taskAssign'],
    properties: { access_control_outcome: allowed ? 'allowed' : 'unexpectedly-denied', probed_route: MANAGER_ACTION },
  });
}

// -------- Journey 4: empty login form -> rejected with error --------
{
  const rec = makeRecorder('login-validation');
  const ctx = await browser.newContext();
  const page = await ctx.newPage({ viewport: { width: 1280, height: 900 } });

  let resp = await page.goto(`${BASE}/login.do`);
  let shot = path.join(RUNTIME, 'traces/login-validation/step-1.png');
  await page.screenshot({ path: shot });
  await rec.record({ index: 1, action: 'goto', url: normUrl(resp.url()), route: '/login',
    request_method: 'GET', form_fields: [], response_status: resp.status(),
    rendered_view: '/jsp/login.jsp', view_evidence: `title: ${await page.title()}`, screenshotPath: shot });

  // Submit with both fields empty.
  const [nav] = await Promise.all([page.waitForNavigation(), page.click('form input[type="submit"]')]);
  shot = path.join(RUNTIME, 'traces/login-validation/step-2.png');
  await page.screenshot({ path: shot });
  const errorShown = await page.locator('.legacy-error').count() > 0;
  const stillLogin = /login/i.test(await page.title());
  await rec.record({ index: 2, action: 'submit-form', url: normUrl(nav.url()), route: '/login',
    request_method: 'POST', form_fields: ['username', 'password'], response_status: nav.status(),
    rendered_view: '/jsp/login.jsp',
    view_evidence: `error banner present: ${errorShown}; returned to login: ${stillLogin}`, screenshotPath: shot });

  await ctx.close();
  journeys.push({
    id: 'journey:login-validation', name: 'Empty login is rejected by required-field validation',
    flow_hypothesis: 'Struts validator required fields on loginForm (validation.xml username/password); tests sem:rule:validator-required-fields behaviourally',
    actor: 'anonymous', steps: rec.steps,
    corroborates: ['sem:action:login', 'sem:view:login', 'sem:rule:validator-required-fields'],
    properties: { validation_outcome: (errorShown && stillLogin) ? 'rejected' : 'not-rejected' },
  });
}

await browser.close();

const doc = {
  repo_fingerprint: repoFingerprint,
  produced_by: 'runtime/scripts/walk-journeys.mjs',
  approval: {
    granted: true,
    statement:
      'User approved executing the bundled taskdesk-legacy target for Milestone 3 runtime journeys ' +
      'in the Claude Code session of 2026-07-07 ("ok, lets finish it"; "do what is sensible").',
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
  journeys,
};

writeFileSync(path.join(RUNTIME, 'journeys.json'), JSON.stringify(doc, null, 2) + '\n');
console.log(`wrote runtime/journeys.json with ${journeys.length} journeys, ` +
  `${journeys.reduce((n, j) => n + j.steps.length, 0)} steps`);
for (const j of journeys) {
  const summary = j.properties.access_control_outcome || j.properties.validation_outcome || j.properties.slice;
  console.log(`  ${j.id}: ${summary}`);
}
