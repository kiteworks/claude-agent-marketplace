# Plugin Security Scan — GitLab CI setup

GitLab-native version of the scanner: static mechanical checks + a Claude
review on Amazon Bedrock, merged into one merge request note, with the job
failing (blocking merge, if configured) on high/critical findings.

## 1. IAM (AWS side) — unchanged from the GitHub version

Same dedicated IAM user, same policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": [
        "arn:aws:bedrock:*::foundation-model/anthropic.claude-sonnet-4-6",
        "arn:aws:bedrock:eu-west-1:<account-id>:inference-profile/eu.anthropic.claude-sonnet-4-6"
      ]
    }
  ]
}
```

The value that goes in the `BEDROCK_MODEL_ID` variable below is the
**inference profile ID** (`eu.anthropic.claude-sonnet-4-6`), not the bare
foundation-model ID — see the IAM policy above, which grants both ARNs.

## 2. GitLab Project Access Token (for posting MR notes)

Settings → Access Tokens → Project access tokens → create one:
- Role: **Reporter** (enough to post/edit notes)
- Scope: **api**
- No expiration shorter than you're comfortable rotating on

Save the token value — you'll only see it once.

> Note the same trust tradeoff as any CI system: this token needs to work on
> every merge request's pipeline, including ones from ordinary feature
> branches, so it can't be restricted to "protected branches only." A
> malicious MR could still see this token if it could get code to run with
> it — which is exactly why the scanner scripts themselves are pulled from
> the **target branch** (`git archive`, in `.gitlab-ci.yml`) rather than the
> MR's own branch. See section 5 below for the one gap that doesn't close.

## 3. CI/CD variables

Settings → CI/CD → Variables → Add variable, for each of:

| Variable | Value | Flags |
|---|---|---|
| `BEDROCK_AWS_ACCESS_KEY_ID` | the IAM user's access key ID | Masked |
| `BEDROCK_AWS_SECRET_ACCESS_KEY` | the IAM user's secret key | Masked, Protected optional |
| `BEDROCK_AWS_REGION` | e.g. `eu-west-1` | — |
| `BEDROCK_MODEL_ID` | `eu.anthropic.claude-sonnet-4-6` | — |
| `PLUGIN_SCANNER_BOT_TOKEN` | the Project Access Token from step 2 | Masked |

Do **not** mark `BEDROCK_AWS_SECRET_ACCESS_KEY` or `PLUGIN_SCANNER_BOT_TOKEN`
as "Protected" unless you also make every branch that opens MRs a protected
branch — GitLab only exposes Protected variables to pipelines running on
protected branches/tags, and MR pipelines run on the *source* branch by
default, which for ordinary feature branches isn't protected. Marking them
Protected without protecting those branches means the scan simply won't have
credentials and will fail closed (reports "ai-review-unavailable", no
blocking Bedrock signal) rather than run.

## 4. Make it a merge requirement

Settings → Merge requests → Merge checks → enable **"Pipelines must
succeed."** Without this, the job still runs and fails, but GitLab won't
stop the merge button from being pressed.

## 5. What this does and doesn't close

**Closed:** the scanner scripts are pulled from the MR's *target* branch via
`git archive` in `.gitlab-ci.yml`, then executed from that trusted copy — an
MR can't edit `security_scan.py` / `ai_review.py` / `aggregate_and_comment.py`
on its own branch to make its own tampering pass, because that edited copy is
never the one that runs.

**Not closed:** `.gitlab-ci.yml` itself is still read from the MR's *source*
branch for ordinary merge request pipelines. A determined MR could edit the
pipeline file directly — e.g. delete the `git archive` step, or point it at
the wrong ref — and that modified pipeline definition would run as written.
Closing this fully means requiring review on changes to `.gitlab-ci.yml` and
`.gitlab/scripts/**` before they can merge:
- **CODEOWNERS** (GitLab Premium+): add a `CODEOWNERS` file requiring a
  specific approver for those paths.
- **Merge request approval rules** (any tier, more manually maintained):
  require approval from a specific group for MRs touching those paths.

## 6. Tuning

- `BLOCK_SEVERITY` in `.gitlab-ci.yml` (`high` by default) controls the
  blocking threshold.
- Static-check logic (bundle drift, manifest permission diffs) lives in
  `.gitlab/scripts/security_scan.py`.
- The AI reviewer's system prompt lives in `.gitlab/scripts/ai_review.py`.
- To run a manual full-repo baseline sweep instead of a normal MR-triggered
  diff scan: CI/CD → Pipelines → **Run pipeline**, set `FULL_SCAN` to
  `true`, leave `BASE_REF`/`HEAD_REF` as their defaults. This makes one
  Bedrock call per existing plugin directory (~40+ here), so expect it to
  take a few minutes and cost roughly that many times a normal scan. Results
  print to the job log only — there's no MR to post a note to in this mode.

## 7. What this scan does and doesn't catch

This is a strong second opinion, not a guarantee. It reads diffs and file
contents; it does not execute anything, so runtime-only behavior won't be
caught by either the static or AI pass. Treat findings as a prioritized list
for human review, especially anything the AI reviewer flags at `medium`
confidence or below.
