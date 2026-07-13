# py-Rizmi — Final Implementation Plan

**Status:** Ready to execute
**Scope:** Packaging & release engineering migration, plus post-1.0 roadmap
**Current library version:** `v1.0.0`

---

## How to use this document

Work top to bottom. Each phase has an explicit **exit criterion** — don't start the next
phase until the current one's is met. This is a checklist, not a reading list: check items
off in your own copy as you go. Phases 0–6 are the packaging migration itself and should be
done in order; Phase 11 (post-1.0 roadmap) is sequenced by dependency, not by calendar —
nothing forces you to do 11.1 before 11.2 except that 11.2 is a bigger lift.

---

## Locked-in decisions (unchanged)

| Area | Decision |
|---|---|
| Layout | `src/py_rizmi/` src-layout, single importable package |
| Distribution | One PyPI package, `pip install py-rizmi[gui]` for extras |
| Build backend | Hatchling + hatch-vcs |
| Dev tooling | `uv` for env/lock/run/build |
| Public API | Only `py_rizmi.__all__` is SemVer-covered |
| CLI | Typer + Rich, resource-first (`rizmi keys …`, `rizmi license …`, `rizmi gui`) |
| GUI | Same repo, behind `[gui]` extra, lazily imported |
| Versioning | SemVer; `.lic` format changes are MAJOR-tier; `schema_version` field from day one |
| Python floor | `>=3.12` |
| Branching | GitHub Flow + on-demand `release/N.x` branches |
| Release gate | Tag → build → auto-publish TestPyPI → **human approval** → publish PyPI |

---

## PHASE 0 — Pre-Flight Corrections
*Planning-document fixes only. Zero code risk. Do this first because it's free.*

- [ ] 0.1 Correct the Python EOL justification: **3.10** EOLs Oct 31, 2026; **3.11** is
      supported into **Oct 2027** (5-year window from its 2022 release). The `>=3.12` floor
      still stands — 3.10's imminent EOL is reason enough, and 3.12 buys a longer runway
      (Ubuntu 24.04 LTS default, supported into 2028) — just don't cite the wrong shared date.
- [ ] 0.2 Rename the planned test file `test_license_token.py` → `test_license_payload.py`,
      target path `tests/unit/models/`, not `tests/unit/core/` — it needs to mirror where the
      module actually ends up living (Phase 2.5).
- [ ] 0.3 Add `tests/gui/test_viewer_view.py` and `tests/gui/test_guide_view.py` to the
      planned test tree — the original list only covered 3 of the 5 GUI views.
- [ ] 0.4 Write a one-paragraph ADR (`docs/adr/0001-pyqt6-licensing.md`) recording the PyQt6
      GPLv3-vs-commercial question as an open risk with an owner and a decision deadline —
      even if today's decision is "defer, revisit before any closed-source Nuitka build ships
      to a paying customer." A risk with a deadline gets resolved; one that only lives in a
      strategy doc gets forgotten.
- [ ] 0.5 **Inventory what packaging config already exists.** The current README's
      `pip install -e ".[dev]"` implies a `pyproject.toml` or `setup.cfg` already exists —
      confirm which, and which build backend it currently declares (most likely plain
      `setuptools`). Phase 2's "write pyproject.toml" is a **migration of an existing file**,
      not a from-scratch creation — go in expecting to reconcile with what's there, not
      overwrite blind.

**Exit criterion:** all five boxes checked, ADR committed.

---

## PHASE 1 — Safety Nets, Before Any Code Changes
*This phase touches the repo, but only ever adds things — it doesn't move or rename a
single existing module yet. Everything here still runs against the current, unmigrated
code on `main`.*

- [ ] 1.1 **Capture golden `.lic` fixtures now**, using today's code. Using the existing
      `issue_license.py` script and `LicenseValidator`, generate a small representative set:
      minimal-fields payload, all-fields-populated payload, a near-expiry payload, and one
      each at 2048/3072/4096-bit key sizes. Commit them — plus their matching public keys —
      under `tests/contract/fixtures/pre_migration/`. This set is your regression oracle for
      the entire restructure; don't regenerate it later against the migrated code, that
      would defeat the point.
- [ ] 1.2 Write a small, throwaway verification script (e.g. `scripts/_verify_fixtures.py`,
      deletable once Phase 6 formalizes it into a real pytest test) that loads every fixture
      from 1.1 and confirms `LicenseValidator` still accepts it. Run it once now to confirm
      the fixtures themselves are valid. Re-run it after every sub-step of Phase 2.
- [ ] 1.3 Stand up a **minimal** `.github/workflows/ci.yml`: lint (if a linter is already
      configured) plus the existing 34 pytest tests, on every push. Deliberately bare-bones —
      Phase 7 expands this later. The point is that Phase 2's restructure gets an automatic
      check on every commit, not just a manual reminder to "run tests."
- [ ] 1.4 Tag the current `main` commit (`git tag pre-migration-baseline`) — an unambiguous
      rollback point if the restructure goes sideways.

**Exit criterion:** fixtures committed and verified, minimal CI green on `main`, baseline tag
pushed.

---

## PHASE 2 — Repository Restructure (src-layout migration)
*Goal: `from py_rizmi import LicenseValidator` works, and the project is buildable and
runnable at every commit along the way — not just at the end. Work on a branch; expect some
intermediate commits on that branch to have failing tests, that's fine, it's not `main`.*

- [ ] 2.0 Create branch `restructure/src-layout` off `main`.
- [ ] 2.1 **Bootstrap `pyproject.toml` first**, before moving any module: update the
      build-system to Hatchling + hatch-vcs and point package discovery at the new
      `src/py_rizmi/` path (even before that path is fully populated). Skipping this step
      means `pip install -e .` / `uv sync` won't resolve anything as you move modules in the
      next steps. Full metadata and extras arrive in Phase 3 — this is just enough to make
      editable installs work.
- [ ] 2.2 Move `src/core/hwid.py` → `src/py_rizmi/core/hwid.py`. Update
      `tests/unit/core/test_hwid.py`'s imports **in the same commit**. Verify with
      `pytest tests/unit/core/test_hwid.py` (not the full suite — other tests are still
      pointing at old paths and are expected to be red until this phase finishes). Re-run the
      Phase 1.2 fixture script. Commit.
- [ ] 2.3 Split RSA/signing primitives out of `keypair.py` / `license_issuer.py` /
      `license_validator.py` into a new `src/py_rizmi/core/crypto.py`. Keep the dependency
      direction **one-way**: `crypto.py` imports nothing from the other three; they import
      from it. This avoids the circular-import bugs that are easy to introduce when splitting
      one file into two. Update matching tests, verify individually, re-run fixture script,
      commit.
- [ ] 2.4 Move `license_issuer.py`, `license_validator.py` → `src/py_rizmi/core/`, importing
      `crypto.py` per 2.3. Update tests, verify, re-run fixture script, commit.
- [ ] 2.5 Create `src/py_rizmi/models/license_payload.py` — `LicensePayload` dataclass with
      `schema_version: int = 1` as the **first field**. Migrate what was `license_token.py`
      into this. Rename the test per Phase 0.2. Verify, re-run fixture script, commit.
- [ ] 2.6 Rename `backend/` → `src/py_rizmi/integrations/`, `license_check.py` →
      `validation.py`. Update its one call site and any docs reference. Verify, commit.
- [ ] 2.7 Move `gui/` → `src/py_rizmi/gui/` as-is — structure doesn't change, only its parent
      path. GUI tests will need `pytest-qt`, which isn't wired up until Phase 6; it's fine if
      GUI tests are simply not runnable yet at this step. Commit.
- [ ] 2.8 Move `utils/logger.py` → `src/py_rizmi/_internal/logging.py`. Verify, commit.
- [ ] 2.9 Delete now-empty `src/core/`, `src/gui/`, `src/utils/`, top-level `backend/`.
- [ ] 2.10 **Update `scripts/*.py` and `main.py` import paths** to the new
      `src/py_rizmi/...` layout — a mechanical find-and-replace, not a rewrite. This keeps
      the project runnable and shippable at this phase boundary, even though the real CLI
      rebuild (Phase 4) and GUI extra split (Phase 5) haven't happened yet. Don't skip this
      just because Phase 4 will eventually replace `scripts/` entirely — that could be weeks
      away, and an unrunnable project in the meantime is a real cost.
- [ ] 2.11 **Update `build.sh`'s Nuitka flags** — the `--include-data-dir`/`--include-data-file`
      paths and the entry-point file — to match the new layout. Run an actual
      `bash build.sh standalone` and confirm the executable still launches before merging.
      This step is easy to forget entirely, since Nuitka builds aren't part of the normal
      `pytest` loop.
- [ ] 2.12 Grep the whole repo (docs, README, any leftover notebooks/configs) for stale old
      import paths and fix every remaining reference.
- [ ] 2.13 Run the full test suite (expect it fully green now) and the Phase 1.2 fixture
      script one final time. Merge `restructure/src-layout` → `main`.

**Exit criterion:** full test suite green on `main`, `main.py` and `rizmi`-equivalent scripts
run correctly, Nuitka standalone build succeeds, fixture script still passes.

---

## PHASE 3 — Public API & Packaging Metadata

- [ ] 3.1 Flesh out `pyproject.toml` from Phase 2.1's bootstrap into the full version:
      project metadata, `[gui]`/`[dev]`/`[all]` extras, `[project.scripts]` entry point (see
      Appendix A). The `rizmi` console-script entry can be declared now even though
      `cli/app.py` doesn't exist until Phase 4 — it just won't resolve until then, which is
      expected, not a bug.
- [ ] 3.2 Populate `src/py_rizmi/__init__.py` with the curated `__all__` re-export surface
      (`LicenseValidator`, `LicenseIssuer`, `KeyPair`, `MachineFingerprint`, `LicensePayload`).
- [ ] 3.3 Add an explicit `__all__` to every subpackage `__init__.py` (`core/`, `models/`,
      `cli/`), not just the top-level one.
- [ ] 3.4 Introduce the `FingerprintProvider` `Protocol` in `core/hwid.py` now, even though
      nothing consumes it yet — this is what makes Phase 11's plugin roadmap non-breaking
      later.
- [ ] 3.5 Write the API stability policy verbatim into `docs/` (SemVer-covered / stable-but-
      not-guaranteed / never-covered `_internal`).
- [ ] 3.6 Add the deprecation-shim pattern (warning + `stacklevel=2`) to `CONTRIBUTING.md` as
      the required approach for any future public-symbol rename or removal.
- [ ] 3.7 **Gitignore `src/py_rizmi/_version.py`.** hatch-vcs generates this file at build
      time from the git tag; committing it causes stale-version bugs and pointless merge
      conflicts. This is a common first-time hatch-vcs mistake.
- [ ] 3.8 Confirm `pip install -e .` and `import py_rizmi` both work cleanly.

**Exit criterion:** `python -c "from py_rizmi import LicenseValidator"` succeeds from a clean
editable install; `__version__` resolves correctly from a git tag.

---

## PHASE 4 — CLI Rebuild (Typer + Rich)

- [ ] 4.1 Add `typer` and `rich` to core dependencies.
- [ ] 4.2 Build the resource-first structure:
      `cli/app.py`, `cli/_console.py`, `cli/commands/{keys,machine_id,license,gui}.py`.
- [ ] 4.3 Port `scripts/gen_keypair.py` → `rizmi keys generate`. Keep flag names
      byte-for-byte where feasible (`--private-out`, `--public-out`, `--key-size`) — anyone
      with existing shell scripts or CI calling the old script should be able to swap in the
      new command with a minimal edit.
- [ ] 4.4 Port `scripts/get_machine_id.py` → `rizmi machine-id` (stays flat, per the original
      reasoning — it isn't really about keys, and forcing it under a group adds a keystroke
      to the most common single action for no organizational benefit).
- [ ] 4.5 Port `scripts/issue_license.py` → `rizmi license issue`.
- [ ] 4.6 Add new `rizmi license validate` and `rizmi license inspect` (Rich table: payload
      fields, expiry status, days remaining).
- [ ] 4.7 Add `rizmi keys validate` (keypair match-check).
- [ ] 4.8 Wire `rizmi gui` with a **deferred** import inside the command function, not at
      module scope — verified explicitly in Phase 5.2, not assumed.
- [ ] 4.9 Set `pretty_exceptions_show_locals=False` on the Typer app; catch domain
      `ValueError`s into a clean one-line Rich panel instead of a raw traceback reaching a
      license-holder's terminal.
- [ ] 4.10 Have every command raise `typer.Exit(code=...)` with a non-zero code on failure
      rather than letting a bare exception propagate — the Phase 6 e2e/CI smoke tests rely on
      exit codes to detect failure correctly.
- [ ] 4.11 Add the `py_rizmi.cli_plugins` entry-points loading loop to `cli/app.py` — inert
      until Phase 11, costs nothing now.
- [ ] 4.12 Decide the fate of `scripts/*.py`: either a thin deprecation-warning wrapper around
      the new CLI for one deprecation window (2 minor releases or 6 months, whichever is
      longer), or outright removal if you're confident nothing external scripts against them.
      Document the choice in the CHANGELOG.

**Exit criterion:** `rizmi --help` shows the full resource-first tree; every ported command
produces identical output to its `scripts/*.py` predecessor on the same inputs.

---

## PHASE 5 — GUI as an Optional Extra

- [ ] 5.1 Move `PyQt6`, `qdarktheme`, `markdown` into `[project.optional-dependencies].gui`.
- [ ] 5.2 **Explicit test, not an assumption:** build a clean venv, `pip install py-rizmi`
      (no extras), confirm `import py_rizmi` and `rizmi --help` succeed, confirm `rizmi gui`
      fails with a friendly "Run: pip install py-rizmi[gui]" message rather than a raw
      `ModuleNotFoundError`. This becomes the Phase 6.6 e2e test — write it as a real test
      now, not just a manual check.
- [ ] 5.3 Grep `cli/app.py` and everything it imports at top level for any accidental
      `import py_rizmi.gui` — this is the single most common way an "optional" extra silently
      stops being optional.
- [ ] 5.4 Resolve the PyQt6/PySide6 question from ADR 0001 (Phase 0.4) before Phase 10's
      1.0 checklist closes, if a paying-customer closed-source build is anywhere on the
      horizon.

**Exit criterion:** no-extras install never imports Qt; `rizmi gui` fails cleanly without
`[gui]` installed and launches correctly with it.

---

## PHASE 6 — Testing Hardening

- [ ] 6.1 Reorganize `tests/` into `unit/{core,cli,models}/`, `integration/`, `contract/`,
      `gui/`, `e2e/`, `regression/` (full tree in Appendix C).
- [ ] 6.2 Add `pytest-cov`, `pytest-qt`, `pytest-mock`, `pytest-xdist`, `pytest-randomly`,
      `hypothesis` to the `[dev]` extra. **Turn on `pytest-randomly` expecting some fallout:**
      if any existing test relies on unnamed shared filesystem state (e.g. writing to a fixed
      `/tmp` path instead of `tmp_path`), random ordering will surface it immediately. Budget
      time for a first round of test-isolation fixes — this is the plugin doing its job, not
      a sign something is broken.
- [ ] 6.3 Formalize the Phase 1.1 golden fixtures into a real pytest test,
      `tests/contract/test_license_format_compat.py` — load `pre_migration/` fixtures, assert
      the current validator still accepts every one. **Don't regenerate the fixtures here**;
      that already happened, correctly, in Phase 1. New fixture sets (`v1_0_0/`, `v1_1_0/`,
      …) get added later, once those schema versions actually exist post-1.0 — keep them in
      a separate subfolder from `pre_migration/` so it's clear which fixtures guard the
      migration versus which guard future schema evolution.
- [ ] 6.4 Add a schema-mismatch contract test: an old validator handed a new-format file (and
      vice versa) fails with a clear "please upgrade" error, not a crash.
- [ ] 6.5 Add `hypothesis` property tests: "for any valid keypair and payload, issue-then-
      validate returns the original payload," and "any single-bit mutation of a signed token
      fails validation."
- [ ] 6.6 Write the e2e smoke test: build a wheel in a clean venv, install it, run
      `rizmi --help` and `rizmi keys generate`; separately assert the Phase 5.2 no-extras GUI
      failure path.
- [ ] 6.7 Set coverage gates: `core/` ≥90%, overall ≥80%, `gui/` ≥60–70% — enforced in CI
      (Phase 7), not aspirational.
- [ ] 6.8 Get GUI tests running headless locally before wiring them into CI. Try
      `QT_QPA_PLATFORM=offscreen` first — it's a lighter-weight headless mode than spinning up
      a full X server, and covers most widget interactions. Fall back to `xvfb`/`xvfb-run`
      only for whatever specific tests actually need a real display server.

**Exit criterion:** full pyramid runs locally (`pytest -m "not slow"` under ~2 min for the
fast tier), coverage gates pass, contract test suite green.

---

## PHASE 7 — CI/CD Pipeline (expanding Phase 1.3's minimal version)

- [ ] 7.1 Expand `ci.yml`: `ruff check` + `mypy`, then fast unit tests as a blocking job on
      every PR and push to `main` (target: under 1–2 min).
- [ ] 7.2 Add a parallel slow-suite job in the same workflow (via `pytest-xdist`):
      integration, contract, GUI (headless per 6.8), on every PR too, but not blocking the
      fast feedback loop.
- [ ] 7.3 Enable `astral-sh/setup-uv`'s built-in dependency caching
      (`with: enable-cache: true`) to keep the fast job fast as the dependency list grows.
- [ ] 7.4 Add `nightly.yml`: scheduled cron, full OS × Python-version matrix (Appendix B) —
      catches environment-specific flakiness without paying that cost on every push.
- [ ] 7.5 Add `release.yml`: triggered on `v*` tag push — build, auto-publish to TestPyPI,
      then **require manual approval** before publishing to PyPI (full workflow in
      Appendix B — this is one workflow, not a separate manual process to remember).
- [ ] 7.6 Branch protection: require passing CI on `main` and any `release/*` branch before
      merge. As sole maintainer, use "requires passing CI, self-merge allowed" rather than a
      "requires review from another person" rule you can't satisfy yourself — add the review
      requirement later if collaborators join.

**Exit criterion:** a throwaway PR shows lint + fast tests + slow tests all running and
passing; a test tag (e.g. `v0.1.0-rc1`) flows through build → TestPyPI automatically.

---

## PHASE 8 — Supply Chain & Security

- [ ] 8.1 Register **two** Trusted Publishers — one on pypi.org, one on test.pypi.org (they're
      separate dashboards) — each naming this exact repo, the `release.yml` workflow file,
      and the matching GitHub Environment (`pypi` / `testpypi`). You can register a "pending"
      publisher **before the project exists on PyPI at all**; it auto-creates the project on
      first successful publish. Don't fall back to a token-based `twine upload` just to
      "create the project first" — that reintroduces the exact risk Trusted Publishing exists
      to remove.
- [ ] 8.2 Confirm no `PYPI_API_TOKEN`-style secret exists anywhere in repo settings; if one
      does from an earlier manual-upload era, revoke it on PyPI and delete the secret.
- [ ] 8.3 Configure the `pypi` GitHub Environment (Settings → Environments) with a required
      reviewer. This is what makes the release workflow safe to leave fully automated — every
      real PyPI publish still needs one human click-through; `testpypi` needs no such gate.
- [ ] 8.4 After the first tagged release, verify via PyPI's Integrity API that a **PEP 740**
      digital attestation was published — as of `gh-action-pypi-publish` v1.11.0+, this
      happens automatically for any Trusted-Publishing release, no extra config needed.
- [ ] 8.5 Pin third-party GitHub Actions to a commit SHA, not a floating tag
      (`actions/checkout@<full-sha>` rather than `@v4`) — a hijacked tag runs with your
      release credentials; this is an actively-exploited real-world vector, not theoretical.
- [ ] 8.6 Set workflow-level `permissions:` explicitly and minimally — `contents: read` by
      default, `id-token: write` only on the specific publish jobs that need it.
- [ ] 8.7 Enable Dependabot (or `uv`'s lock-update automation) specifically for
      `cryptography` and `PyJWT` — these two are your actual security-relevant attack surface.
- [ ] 8.8 Add `SECURITY.md` with a responsible-disclosure contact and expected response
      window.

**Exit criterion:** a real `git tag v0.1.0 && git push --tags` produces a TestPyPI release
with no manual step beyond the one required PyPI approval click.

---

## PHASE 9 — Documentation

- [ ] 9.1 Generate an API reference from docstrings (`mkdocs` + `mkdocstrings`, or Sphinx —
      whichever you're already comfortable with).
- [ ] 9.2 Write a migration guide mapping every old `scripts/*.py` invocation to its new
      `rizmi …` equivalent, one line each.
- [ ] 9.3 Start `CHANGELOG.md` in Keep-a-Changelog format, tied to `hatch-vcs` tags.
- [ ] 9.4 Update `CONTRIBUTING.md` for the new `src/py_rizmi/` layout and the deprecation-shim
      requirement (Phase 3.6).
- [ ] 9.5 Update the in-app Integration Guide view's rendered content (it's your own README)
      so its Python API examples use `from py_rizmi import …`, not the old deep
      `src.core.*` paths.
- [ ] 9.6 Update the root README's Quick Start to `pip install py-rizmi[gui]` (or
      `pip install -e ".[gui]"` for local dev) instead of `pip install -r requirements.txt` —
      the old instructions go stale the moment the new extras exist.

**Exit criterion:** a new contributor can go from `git clone` to a passing test suite using
only the README and CONTRIBUTING.md, with no tribal knowledge required.

---

## PHASE 10 — v1.0.0 Release Checklist

- [ ] 10.1 Public API (`__all__` surface) is frozen and documented.
- [ ] 10.2 `.lic` format has `schema_version=1` and the Phase 6.3 contract test is green in
      CI.
- [ ] 10.3 CI is green across the full OS × Python-version matrix.
- [ ] 10.4 CLI command structure from Phase 4 is final — no more renames planned.
- [ ] 10.5 CHANGELOG process is live with at least one real entry.
- [ ] 10.6 **Dry-run the entire release pipeline on a release-candidate tag** (e.g. `v0.9.0`
      or `v1.0.0-rc1`) before cutting the real `v1.0.0` — confirm build → TestPyPI →
      (approval) → PyPI all work end-to-end on a tag you're comfortable yanking if something's
      wrong. Exact `git tag` / `gh release create` commands are in the **Version & Release
      Management** section right after this phase — use its "release-candidate" recipe here.
- [ ] 10.7 Tag `v1.0.0` for real (see the **Version & Release Management** section's "cutting
      a normal release" recipe for the exact commands). Approve the PyPI publish step. Verify
      the PEP 740 attestation appears (Phase 8.4). Once this lands, `v1.0.0` is the project's
      current version — every release after this point (including all of Phase 11) follows
      that same playbook.

**Exit criterion:** `pip install py-rizmi` from a stranger's clean machine works, and
`pip install py-rizmi[gui]` launches the GUI.

---

## Version & Release Management — Git Tags + `gh release`

*This isn't a one-time phase — it's the standing playbook you reuse for every release from
here on, starting the moment Phase 10.7 lands. The plan's Locked-in decisions already define
the release **gate** (tag → build → TestPyPI → human approval → PyPI); this section is the
actual commands that drive it, including the GitHub Release page itself, which nothing above
creates automatically.*

**Where this project stands right now:** current version is **`v1.0.0`**. Every example
below assumes that tag already exists and `main` sits at that commit.

### Versioning source of truth
- hatch-vcs (Phase 2.1 / 3.7) derives `__version__` purely from the latest git tag reachable
  from `HEAD`. Never hand-edit a version string anywhere in the codebase — if it's wrong,
  the tag is wrong, not a file.
- Tag format is `vMAJOR.MINOR.PATCH` (`v1.0.0`, `v1.0.1`, `v1.1.0`, …). Keep the `v` prefix —
  `release.yml`'s trigger (`push: tags: ["v*"]`, Appendix B) matches on it.

### What bump to use for what
| Change | Bump | Example |
|---|---|---|
| Bug fix, no public-API or `.lic` format change | PATCH | `v1.0.0` → `v1.0.1` |
| New feature, backward-compatible (e.g. Phase 11.1 key rotation) | MINOR | `v1.0.0` → `v1.1.0` |
| Anything touching the `__all__` surface or `.lic` `schema_version` (per the Locked-in decisions table) | MAJOR | `v1.0.0` → `v2.0.0` |

### Cutting a normal release (patch or minor) from `main`
1. Confirm CI is green on `main`.
2. Update `CHANGELOG.md` (Keep-a-Changelog format, Phase 9.3): move "Unreleased" into a new
   `## [1.1.0] - 2026-07-13` heading. Commit: `git commit -m "Prepare release v1.1.0"`.
3. Create an **annotated** tag — not lightweight; `gh release create --verify-tag` and
   hatch-vcs both expect real tag metadata:
   ```bash
   git tag -a v1.1.0 -m "Release v1.1.0"
   git push origin v1.1.0
   ```
4. The pushed tag triggers `release.yml`: build → auto-publish to TestPyPI → waits for the
   required reviewer on the `pypi` Environment (Phase 8.3). Approve it in the Actions tab.
5. Once `publish-pypi` succeeds, verify the PEP 740 attestation (Phase 8.4).
6. Create the matching GitHub Release — the tag push alone does **not** do this:
   ```bash
   gh release create v1.1.0 \
     --title "v1.1.0" \
     --notes-file <(awk '/## \[1.1.0\]/{f=1;next}/## \[/{f=0}f' CHANGELOG.md) \
     --verify-tag
   ```
   `--verify-tag` refuses to run if the tag isn't on the remote yet — catches a typo before
   it becomes a public release.
7. Optional: attach the Nuitka standalone binaries (see "Building an Executable" in the
   README) once built per-OS:
   ```bash
   gh release upload v1.1.0 dist/py-rizmi-linux dist/py-rizmi-windows.exe
   ```

### Cutting a release-candidate (Phase 10.6's dry run)
```bash
git tag -a v1.0.0-rc1 -m "Release candidate v1.0.0-rc1"
git push origin v1.0.0-rc1
gh release create v1.0.0-rc1 \
  --title "v1.0.0-rc1" \
  --notes "Release candidate — dry run of the full release pipeline." \
  --prerelease --verify-tag
```
`--prerelease` keeps it out of "Latest release," so an unpinned `pip install py-rizmi` can
never accidentally resolve to an rc build.

### Hotfix on an already-shipped version (Branching decision: `release/N.x`)
If `v1.0.0` shipped, `main` has already moved on toward `v1.1.0`, but `v1.0.0` needs an
urgent patch:
```bash
git checkout -b release/1.x v1.0.0
git cherry-pick <sha-of-the-fix-from-main>
git tag -a v1.0.1 -m "Release v1.0.1"
git push origin release/1.x v1.0.1
gh release create v1.0.1 --title "v1.0.1" --notes "Hotfix: <one-line summary>" --verify-tag
```

### Quick command reference
| Task | Command |
|---|---|
| List existing tags, newest first | `git tag -l "v*" --sort=-v:refname` |
| Show what a tag points to | `git show v1.0.0 --stat` |
| Delete a bad tag before anyone's pulled it | `git tag -d v1.1.0 && git push origin :refs/tags/v1.1.0` |
| List GitHub Releases | `gh release list` |
| View a release | `gh release view v1.0.0` |
| Edit release notes after the fact | `gh release edit v1.0.0 --notes-file CHANGELOG.md` |

**Exit criterion:** you can go from "CHANGELOG updated" to "PyPI has the new version and
GitHub shows a matching Release" using only the commands above — no manual step beyond the
one required PyPI approval click.

---

## PHASE 11 — Post-1.0 Product Roadmap

*Straight from your own README's "Ideas for Contributions" — not generic suggestions, this
is the actual shape of what comes next.*

- [ ] **11.1 (v1.1, additive/minor) Key rotation** — add `key_id` to the JWT header,
      `LicenseValidator` resolves the right public key by `key_id`. No breaking change; new
      `rizmi keys rotate` command.
- [ ] **11.2 (first genuine multi-package split point) License server / online validation** —
      a server-side ping endpoint for revocation/heartbeat checks. This is where a `uv`
      workspace split actually earns its keep: a web framework + database dependency
      footprint, and an ops/infra audience that runs it as a service and never
      `pip install py_rizmi` into their own code. Split into its own package at this point,
      not before.
- [ ] **11.3 Certificate Revocation List (CRL) support** — builds on 11.2's server; a
      `rizmi crl revoke <license-id>` admin command plus a validator-side CRL check.
- [ ] **11.4 Tamper-evident audit log** — rolling SHA-256 hash chains over issuance/validation
      events, for compliance-sensitive deployments.
- [ ] **11.5 (evaluate only, don't commit yet) GUI as a standalone product** — revisit only
      if the GUI becomes something marketed to a business-user audience distinct from the
      developer-library audience, and only after ADR 0001's PyQt6/PySide6 question is
      actually resolved.

---

## Appendix A — `pyproject.toml` (target state, after Phase 3)

```toml
[build-system]
requires = ["hatchling", "hatch-vcs"]
build-backend = "hatchling.build"

[project]
name = "py-rizmi"
dynamic = ["version"]
description = "Offline RSA-signed license management — CLI, GUI, and Python API."
readme = "README.md"
license = "MIT"
requires-python = ">=3.12"
authors = [{ name = "Ramzi Hadrouk" }]
dependencies = [
    "PyJWT>=2.8",
    "cryptography>=42.0",
    "typer>=0.12",
    "rich>=13.0",
]

[project.optional-dependencies]
gui = ["PyQt6>=6.6", "qdarktheme", "markdown"]
dev = [
    "pytest>=8.0",
    "pytest-cov",
    "pytest-qt",
    "pytest-mock",
    "pytest-xdist",
    "pytest-randomly",
    "hypothesis",
    "ruff",
    "mypy",
]
all = ["py-rizmi[gui]"]

[project.scripts]
rizmi = "py_rizmi.cli.app:main"

[tool.hatch.version]
source = "vcs"

[tool.hatch.build.hooks.vcs]
version-file = "src/py_rizmi/_version.py"

[tool.hatch.build.targets.wheel]
packages = ["src/py_rizmi"]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.mypy]
python_version = "3.12"
strict = true

[tool.pytest.ini_options]
markers = ["slow: slower integration/GUI/e2e tests"]
testpaths = ["tests"]
```

```gitignore
# .gitignore addition — Phase 3.7
src/py_rizmi/_version.py
```

---

## Appendix B — GitHub Actions workflows

**`.github/workflows/ci.yml`** (Phase 1.3 minimal version → Phase 7 full version shown)
```yaml
name: CI
on:
  pull_request:
  push:
    branches: [main]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
        with:
          enable-cache: true
      - run: uv run ruff check .
      - run: uv run mypy src

  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
        with:
          enable-cache: true
      - run: uv sync --extra dev
      - run: uv run pytest tests/unit -m "not slow" --cov=py_rizmi --cov-fail-under=80

  slow-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
        with:
          enable-cache: true
      - run: sudo apt-get update && sudo apt-get install -y xvfb
      - run: uv sync --extra dev --extra gui
      - run: |
          export QT_QPA_PLATFORM=offscreen
          uv run pytest tests/integration tests/contract tests/gui tests/e2e
```

**`.github/workflows/nightly.yml`**
```yaml
name: Nightly Full Matrix
on:
  schedule:
    - cron: "0 3 * * *"

jobs:
  full-matrix:
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
        python-version: ["3.12", "3.13"]
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - run: uv sync --extra dev --extra gui --python ${{ matrix.python-version }}
      - run: uv run pytest
```

**`.github/workflows/release.yml`** — build once, publish to TestPyPI automatically,
require one human approval before PyPI. Register the `pypi` and `testpypi` Environments
under repo Settings → Environments first (Phase 8.1/8.3), with a required reviewer on `pypi`
only.
```yaml
name: Release
on:
  push:
    tags: ["v*"]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: astral-sh/setup-uv@v3
      - run: uv build
      - uses: actions/upload-artifact@v4
        with:
          name: dist
          path: dist/

  publish-testpypi:
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: testpypi
      url: https://test.pypi.org/p/py-rizmi
    permissions:
      id-token: write
    steps:
      - uses: actions/download-artifact@v4
        with:
          name: dist
          path: dist/
      - uses: pypa/gh-action-pypi-publish@release/v1
        with:
          repository-url: https://test.pypi.org/legacy/

  publish-pypi:
    needs: publish-testpypi
    runs-on: ubuntu-latest
    environment:
      name: pypi           # required reviewer configured on this Environment — human
      url: https://pypi.org/p/py-rizmi   # approval happens here, workflow itself is automatic
    permissions:
      id-token: write
    steps:
      - uses: actions/download-artifact@v4
        with:
          name: dist
          path: dist/
      - uses: pypa/gh-action-pypi-publish@release/v1
        # PEP 740 attestations generated and uploaded automatically, v1.11.0+
```

---

## Appendix C — Final test tree

```
tests/
├── conftest.py
├── unit/
│   ├── core/
│   │   ├── test_hwid.py
│   │   ├── test_keypair.py
│   │   ├── test_license_issuer.py
│   │   └── test_license_validator.py
│   ├── models/
│   │   └── test_license_payload.py        # was test_license_token.py — Phase 0.2
│   └── cli/
│       └── test_cli_commands.py
├── integration/
│   ├── test_issue_validate_roundtrip.py
│   └── test_integrations_validation.py
├── contract/
│   ├── fixtures/
│   │   ├── pre_migration/{license.lic, public_key.pem, ...}   # Phase 1.1 — migration guard
│   │   ├── v1_0_0/{license.lic, public_key.pem}                # post-1.0 — schema guard
│   │   └── v1_1_0/{license.lic, public_key.pem}
│   └── test_license_format_compat.py
├── gui/
│   ├── test_hwid_view.py
│   ├── test_keymanager_view.py
│   ├── test_generate_view.py
│   ├── test_viewer_view.py                # added — Phase 0.3
│   └── test_guide_view.py                 # added — Phase 0.3
├── e2e/
│   └── test_installed_package_smoke.py
└── regression/
    └── test_issue_042_hwid_case_sensitivity.py
```
