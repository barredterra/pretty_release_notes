Turn GitHub's auto-generated release notes into human-readable sentences.

Converts this:

![Original](img/original.png)

Into this:

![Modified](img/modified.png)

> [!WARNING]
> The prompt is geared towards [ERPNext](https://github.com/frappe/erpnext) and the [Frappe Framework](https://github.com/frappe/frappe). If you want to use this for different projects, please fork and adjust to your liking.

## Configuration

Copy `.env.example` to `.env` and fill in your GitHub token and OpenAI API key.

You can choose a database type by setting the `DB_TYPE` environment variable. Currently supported are `csv` and `sqlite`.

## Usage

```bash
source env/bin/activate

python main.py --help
python main.py erpnext v15.38.4 # using DEFAULT_OWNER from .env
python main.py --owner alyf-de banking v0.0.1
```

Example output:

```markdown
---- Original ----
## What's Changed
* fix: list view and form status not same for purchase order (backport #43690) (backport #43692) by @mergify in https://github.com/frappe/erpnext/pull/43706


**Full Changelog**: https://github.com/frappe/erpnext/compare/v15.38.3...v15.38.4

---- Modified ----
## What's Changed
* Removes unnecessary decimal precision checks for _per_received_ and _per_billed_ fields in **Purchase Order**, so the list view status and form status remain consistent. https://github.com/frappe/erpnext/pull/43706


**Full Changelog**: https://github.com/frappe/erpnext/compare/v15.38.3...v15.38.4
**Authors**: @rohitwaghchaure
```
