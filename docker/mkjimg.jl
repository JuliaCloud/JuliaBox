require("/home/juser/build_sysimg.jl")

println("Building JuliaBox Julia system image...")
build_sysimg("/home/juser/.juliabox/jimg/sys", "native", "/home/juser/jimg.jl", force=true)