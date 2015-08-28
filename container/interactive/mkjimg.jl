include(joinpath(JULIA_HOME, Base.DATAROOTDIR, "julia", "build_sysimg.jl"))

println("Building JuliaBox Julia system image...")
build_sysimg("/opt/julia_packages/jimg/stable/sys", "native", "/home/juser/jimg.jl", force=true)