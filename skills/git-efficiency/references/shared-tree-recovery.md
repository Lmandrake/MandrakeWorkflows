# Recovering work in a shared git tree

Read this when work looks lost after a stash, pull, merge, rebase or a commit
that swept up someone else's files, or when publishing from a tree that is never
clean.

## Before concluding anything is lost

- **A slow mount can serve stale reads across processes.** On WSL drvfs and
  similar mounts, `git status`, `grep` and `tail` can show pre-write content for
  a couple of minutes after a write landed durably. Re-read before any recovery;
  don't re-apply work that was never lost.
- **A clean `git status` after a stash can mimic a revert** when the stash never
  popped back. Check `git stash list` and `git reflog` first.
- **Dangling content is recoverable:** `git fsck --unreachable | grep commit`,
  then `git cat-file -p <sha>` / diff the commit against its parent. Re-diff the
  recovered tree against what was stashed before trusting it.

## A refused `git merge` can revert the tree

With autostash on (`merge.autoStash`/`rebase.autoStash`, or a wrapper that
stashes), after "Your local changes ... would be overwritten by merge" git stashes,
hard-resets to HEAD, then re-applies the stash. If another process holds
`index.lock` at that instant the re-apply fails and every tracked edit stays
reverted, with nothing in the reflog (HEAD never moved). The stash survives only
as a dangling `WIP on <branch>` commit; recover it with the `fsck` recipe above.
(Observed mechanism from one incident, not verified across git versions.)

Prevention: merge in a private `git worktree add --detach` and push
`HEAD:<branch>` from there. In the shared tree, a PreToolUse hook can refuse
`git merge` (bar `--ff-only`), bare `git pull`, `--autostash`, and whole-tree
`reset --hard` / `checkout .` / `restore .` / pathless `stash` / `clean -f`.

## Publishing from a tree that is never clean

Where tracked files are always dirty (daemons, generated dashboards, peers
mid-edit), `pull --rebase` refuses and a fast-forward fails once diverged. Prefer
giving each writer its own clone. Otherwise:

1. `<base>` = parent of the oldest commit in
   `git rev-list --cherry-pick --right-only --no-merges origin/main...HEAD`
   (replaying commits already upstream re-creates them as empty duplicates).
2. `git replay --ref-action=print --onto origin/main <base>..HEAD` rebuilds the
   local commits in the object store, touching neither worktree nor index.
   `git replay` is experimental and its options vary by version: check
   `git replay -h` first.
3. Push the printed sha to `refs/heads/main`.
4. `git reset --keep origin/main`: updates only files upstream changed, keeps
   every uncommitted edit, and aborts rather than overwrite a file that is both.

Regenerated artifacts that clash every time can simply take upstream's copy
first.

## A pushed commit with the wrong story

If a pushed commit has the right content but the wrong message (e.g. it swept up
another agent's files), annotate rather than rewrite:
`git notes add -m "..." <sha>`, read with `git notes show <sha>`. Notes do not
travel by default: `git push origin 'refs/notes/*'`, and other checkouts need
`git fetch origin 'refs/notes/*:refs/notes/*'` to see them.

## WSL: Windows Git Credential Manager from a linked worktree

GCM can fail from a linked worktree ("not a git repository: (NULL)") while the
main tree pushes fine. Per call:
`git -c credential.helper= -c credential.helper='!gh auth git-credential' push ...`
