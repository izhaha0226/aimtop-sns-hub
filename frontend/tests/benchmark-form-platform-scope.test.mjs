import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

const __dirname = dirname(fileURLToPath(import.meta.url))
const sourcePath = join(__dirname, '..', 'src', 'app', '(main)', 'clients', '[id]', 'benchmark', 'page.tsx')
const source = readFileSync(sourcePath, 'utf8')

function assertIncludes(snippet, message) {
  assert.ok(source.includes(snippet), message)
}

function assertControlScoped(field) {
  assertIncludes(`key={\`${'${platform}'}-${field}\`}`, `${field} control must remount per platform`)
  assertIncludes(`id={\`benchmark-${'${platform}'}-${field}\`}`, `${field} control id must include platform`)
  assertIncludes(`name={\`benchmark-${'${platform}'}-${field}\`}`, `${field} control name must include platform`)
  assertIncludes(`data-testid={\`benchmark-${'${platform}'}-${field}\`}`, `${field} control data-testid must include platform`)
}

assertIncludes('const [formsByPlatform, setFormsByPlatform]', 'account drafts must be separated by platform')
assertIncludes('const form = formsByPlatform[platform] || DEFAULT_ACCOUNT_FORM', 'visible account form must read the active platform draft')
assertIncludes('[platform]: {', 'form updates must write only the active platform draft')
assertIncludes('const changePlatform = useCallback((nextPlatform: string) => {', 'tab switch must go through changePlatform')
assertIncludes('setEditingId(null)', 'tab switch must close edit mode')
assertIncludes('setManualPostOpenId(null)', 'tab switch must close manual post panel')
assertIncludes('setFormsByPlatform((prev) => ({ ...prev, [nextPlatform]: emptyAccountForm() }))', 'tab switch must clear the target platform registration draft to prevent stale handle values')
assertIncludes('setPlatform(nextPlatform)', 'tab switch must activate the requested platform')
assertIncludes('onClick={() => changePlatform(item)}', 'platform tabs must call changePlatform')
assertIncludes('data-testid={`benchmark-platform-tab-${item}`}', 'platform tabs must expose platform-scoped test ids for smoke tests')
assertIncludes('aria-pressed={platform === item}', 'platform tabs must expose selected state for browser smoke tests')
assertIncludes('key={`benchmark-account-form-${platform}`}', 'account form wrapper must remount per platform')
assertIncludes('data-testid={`benchmark-account-form-${platform}`}', 'account form wrapper data-testid must include platform')
assertIncludes('data-platform={platform}', 'account form wrapper must expose active platform for browser smoke tests')

for (const field of ['handle', 'purpose', 'source-type', 'metadata', 'memo']) {
  assertControlScoped(field)
}

for (const field of ['handle', 'metadata', 'memo']) {
  assertIncludes(`autoComplete="off"`, `${field} text input must disable browser autofill`)
}

console.log('benchmark form platform scoping checks passed')
