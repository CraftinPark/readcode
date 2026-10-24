"""Print a compact view of fix commits: subject, short body, non-test diff, added test names."""
import subprocess, sys, re
repo, shas = sys.argv[1], sys.argv[2:]
TEST = re.compile(r"(^|/)(tests?|__tests__|spec)(/|$)|_test\.|test_|CHANGELOG|\.md$|\.graphql$|schema\.|\.lock$", re.I)
def git(*a):
    return subprocess.run(["git", "-C", repo, *a], capture_output=True, text=True, encoding="utf-8", errors="replace").stdout
for sha in shas:
    print("#" * 10, sha)
    print("\n".join(git("show", "-s", "--format=%s%n%b", sha).splitlines()[:10]))
    files = [f for f in git("show", "--format=", "--name-only", sha).split("\n") if f]
    code = [f for f in files if not TEST.search(f)]
    tests = [f for f in files if TEST.search(f) and "CHANGELOG" not in f]
    d = git("show", "--format=", "-U3", sha, "--", *code).splitlines()
    d = [l for l in d if not l.startswith(("index ", "diff --git"))]
    print("\n".join(d[:70]) + ("\n...[truncated]" if len(d) > 70 else ""))
    t = git("show", "--format=", sha, "--", *tests)
    names = re.findall(r"^\+\s*(?:async )?(?:def|fn|void|public void) (test\w*|\w+_test\w*)", t, re.M)
    names += re.findall(r"^\+\s*(?:#\[test\]|@Test)\s*$\n\+\s*(?:public )?(?:async )?(?:fn|void) (\w+)", t, re.M)
    print("TESTS:", tests[:3], names[:4])
