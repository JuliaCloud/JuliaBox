## JuliaBox - Hosted IJulia Containers

Try [JuliaBox](http://www.juliabox.org). Join our [Mailing List](https://groups.google.com/forum/#!forum/julia-box)

Our goal is to make it easy for users of Julia to access and run Julia
anywhere without any fuss. Use Julia through the browser, access tons
of processors and memory, suck in data from anywhere, and have it
always accessible through any device you use so long as it has a
browser.

Currently, the primary usage model is IJulia notebooks. We also have a
shell, and we plan to make it easy to do things such as deploying your
Julia code server-side behind REST APIs, without having to deal with
all the hassle of infrastructure management.

The only constraint is imagination (and server cost).

### Features

- Runs each IJulia session in its own sandboxed container.
- A bash session is also started in the container - can be used to run the Julia console REPL.
- File transfer facility into a session's container.
- File synchronization with remote git repositories &amp; Google Drive.
- Basic admin screen to delete old/inactive sessions.
- Login via. Google authentication.
- Auto cleanup of sessions based on inactivity.
- Ability to limit memory and CPU allocated for user sessions.
- [Packages installed](PACKAGES.md)
