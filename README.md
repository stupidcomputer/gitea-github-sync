# gitea-github-sync

Automatically mirror from a private code forge to Github, and bidirectionally synchronize issues between two repos

## Implementation notes

- The implementation matches up issue numbers, instead of coorelating them with a database or something. This is fine because we're only using this software on repos that have no issues (e.g. are brand new) and so therefore all the issue numbers will line up. For two mirrors with different issues, you'll have to pick one side to keep and another to purge.

## License

Licensed under the GNU Affero v3 license. (c) 2024 randomuser, stupidcomputer, etc.