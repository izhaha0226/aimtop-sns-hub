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
assertIncludes('const changePlatform = useCallback((nextPlatform: string) => {', 'tab switch must go through changePlatform')
assertIncludes('setEditingId(null)', 'tab switch must close edit mode')
assertIncludes('onClick={() => changePlatform(item)}', 'platform tabs must call changePlatform')
assertIncludes('key={`benchmark-account-form-${platform}`}', 'account form wrapper must remount per platform')
assertIncludes('data-testid={`benchmark-account-form-${platform}`}', 'account form wrapper data-testid must include platform')

for (const field of ['handle', 'purpose', 'source-type', 'metadata', 'memo']) {
  assertControlScoped(field)
}

for (const field of ['handle', 'metadata', 'memo']) {
  assertIncludes(`autoComplete="off"`, `${field} text input must disable browser autofill`)
}

console.log('benchmark form platform scoping checks passed')
