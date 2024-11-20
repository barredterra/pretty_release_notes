Turn GitHub's auto-generated release notes into human-readable sentences.

Converts this:

![Original](img/original.png)

Into this:

![Modified](img/modified.png)

> [!WARNING]
> Currently, the prompt and default parameters are geared towards [ERPNext](https://github.com/frappe/erpnext) and the [Frappe Framework](https://github.com/frappe/frappe). If you want to use this for different projects, please fork and adjust to your liking.

## Configuration

Copy `.env.example` to `.env` and fill in your GitHub token and OpenAI API key.

## Usage

```bash
source env/bin/activate

python main.py --help
python main.py erpnext v15.38.4
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
* We have fixed an issue where the status in the **Purchase Order** list view differed from the form, ensuring both now accurately reflect the _To Bill_ status as intended. https://github.com/frappe/erpnext/pull/43706


**Full Changelog**: https://github.com/frappe/erpnext/compare/v15.38.3...v15.38.4
```

> [!NOTE]
> Currently we only support release notes as generated by GitHub (bullet points with the PR URL at the end).
