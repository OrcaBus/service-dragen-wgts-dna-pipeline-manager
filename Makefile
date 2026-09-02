.PHONY: test test-app test-app-all check fix install

check:
	@pnpm audit
	@pnpm prettier
	@pnpm lint
	@pre-commit run --all-files

fix:
	@pnpm prettier-fix
	@pnpm lint-fix

install:
	@pnpm install --frozen-lockfile

test:
	@pnpm test

test-app:
	@pytest -m "not sfn_teststate" --tb=short

test-app-all:
	@pytest --tb=short
