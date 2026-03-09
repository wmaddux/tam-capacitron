# Configuration management (CM) routine

## Branch naming

- **main** – Stable, shippable state. Protect or use as the default branch.
- **feature/<name>** – New capability (e.g. `feature/load-from-collectinfo`).
- **fix/<name>** – Bug or small fix (e.g. `fix/slider-defaults`).

## Commit frequency

- Commit when a logical unit of work is done (one feature, one fix, or one refactor). Avoid large commits that mix unrelated changes.
- Prefer smaller, reviewable commits so history stays clear and rollback is easier.

## When to tag or release

- Tag when you have a version worth referring to later (e.g. `v0.1.0` for first working UI + engine).
- Use semantic-style versions if you adopt releases: `v0.y.z` for pre-1.0, `v1.y.z` for stable.

## Push workflow

1. Pull before starting work: `git pull origin main` (or your target branch).
2. Create a branch for non-trivial work: `git checkout -b feature/my-feature`.
3. Commit and push: `git push -u origin feature/my-feature`.
4. Open a pull request into `main` (or merge locally and push `main` after review).
5. After merge, pull `main` again before next branch.

## First push (Phase 0)

As soon as the first bit of working software exists (e.g. minimal engine or scaffold), push to GitHub so the repo is the single source of truth.

- **Remote:** `origin` → `https://github.com/wmaddux/tam-capacitron.git`
- **Auth:** Use SSH (`git@github.com:wmaddux/tam-capacitron.git`) or HTTPS with a [personal access token](https://github.com/settings/tokens). Ensure you have push access.
- **Push:** `git push -u origin main` (or your branch). Resolve auth if prompted (SSH key or token).

Once the first push is done, Phase 0 is complete (see [PLAN.md](PLAN.md)).
