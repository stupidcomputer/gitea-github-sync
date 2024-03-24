# gitea-github-sync

synchronize git repos, and associated issues, prs, and other repo metadata

## things to do
- [ ] write a nix derivation for [giteapy](https://github.com/dblueai/giteapy)
	- [ ] integrate it into the shell.nix
- [ ] define configuration
- [ ] do the main thing
	- [ ] standardize the issue, pr, and other event objects
	- [ ] write a 'diff' function to return the delta between two objects
	- [ ] return a series of api calls to reconcile the problems
	- [ ] handle race conditions?
- [ ] write documentation

## license
licensed agpl. see LICENSE for more details.
gitea-github-sync is copyright rndusr, randomuser, stupidcomputer, et. al. 2024
