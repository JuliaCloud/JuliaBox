## JuliaBox

JuliaBox is hosted online at
[http://www.juliabox.org/](http://www.juliabox.org). Join our [Mailing
List](https://groups.google.com/forum/#!forum/julia-box).

Our goal is to provide the best Julia experience we can. We want to
make it easy for Julia users to run Julia anywhere without too much
fuss. Use Julia through the browser, access lots of processors and
memory, suck in data from anywhere, and have it always accessible
through any device you use so long as it has a browser.

The only constraint is imagination (and server cost).

## Features

- Run [IJulia](https://github.com/JuliaLang/IJulia.jl) sessions
    - A bash session is also started in the container, which can be used to run the Julia REPL.
    - File transfer facility into a session's container.
    - File synchronization with Google Drive.
    - Clone Github repositories.
    - Login via Google authentication. Submit a PR for more auth methods!
- Expose Julia packages &amp; functions as REST APIs using [JuliaWebAPI](https://github.com/tanmaykm/JuliaWebAPI.jl)
    - Scale with requests.
- Sandboxed [Docker](http://www.docker.com) containers.
- Basic admin screen to delete old and inactive sessions.
- Auto cleanup of sessions and API servers based on inactivity.
- Ability to limit CPU, memory, and disk space for user sessions and APIs.

## Docs

- [Architecture](docs/Architecture.md)
- [Installation](docs/INSTALL.MD)