require("/home/juser/build_sysimg.jl")

println("Building JuliaBox Julia system image...")
build_sysimg("/opt/julia_packages/jimg/stable/sys", "native", "/home/juser/jimg.jl", force=true)

# create the JuliaBox Julia profile
# TODO: this should probably be merged with IJulia deps
eprintln(x...) = println(STDERR, x...)
eprintln("Creating julia profile in IPython...")

include(joinpath(Pkg.dir("IJulia"), "deps", "ipython.jl"))
const ipython, ipyvers = find_ipython()
const profile_name = "jboxjulia"
const custom_args = ["-J", "/opt/julia_packages/jimg/stable/sys.ji"]

run(`$ipython profile create $profile_name`)

juliaprof = chomp(readall(`$ipython locate profile $profile_name`))

function add_config(prof::String, s::String, val, overwrite=false)
    p = joinpath(juliaprof, prof)
    r = Regex(string("^[ \\t]*c\\.", replace(s, r"\.", "\\."), "\\s*=.*\$"), "m")
    if isfile(p)
        c = readall(p)
        if ismatch(r, c)
            m = replace(match(r, c).match, r"\s*$", "")
            if !overwrite || m[search(m,'c'):end] == "c.$s = $val"
                eprintln("(Existing $s setting in $prof is untouched.)")
            else
                eprintln("Changing $s to $val in $prof...")
                open(p, "w") do f
                    print(f, replace(c, r, old -> "# $old"))
                    print(f, """
c.$s = $val
""")
                end
            end
        else
            eprintln("Adding $s = $val to $prof...")
            open(p, "a") do f
                print(f, """

c.$s = $val
""")
            end
        end
    else
        eprintln("Creating $prof with $s = $val...")
        open(p, "w") do f
            print(f, """
c = get_config()
c.$s = $val
""")
        end
    end
end

# add Julia kernel manager if we don't have one yet
if VERSION >= v"0.3-"
    binary_name = "julia"
else
    binary_name = "julia-basic"
end

kernel_cmd_params = ["$(escape_string(joinpath(JULIA_HOME,(@windows? "julia.exe":"$binary_name"))))"]
!isempty(custom_args) && append!(kernel_cmd_params, custom_args)
append!(kernel_cmd_params, ["-i", "-F", "$(escape_string(joinpath(Pkg.dir("IJulia"),"src","kernel.jl")))", "{connection_file}"])
kernel_cmd = "[\"$(join(kernel_cmd_params,"\",\""))\"]"

add_config("ipython_config.py", "KernelManager.kernel_cmd", kernel_cmd, true)

# make qtconsole require shift-enter to complete input
add_config("ipython_qtconsole_config.py",
           "IPythonWidget.execute_on_complete_input", "False")

add_config("ipython_qtconsole_config.py",
           "FrontendWidget.lexer_class", "'pygments.lexers.JuliaLexer'")

# set Julia notebook to use a different port than IPython's 8888 by default
add_config("ipython_notebook_config.py", "NotebookApp.port", 8998)

#######################################################################
# Copying files into the correct paths in the profile lets us override
# the files of the same name in IPython.

rb(filename::String) = open(readbytes, filename)
eqb(a::Vector{Uint8}, b::Vector{Uint8}) =
    length(a) == length(b) && all(a .== b)

# copy IJulia/deps/src to destpath/destname if it doesn't
# already exist at the destination, or if it has changed (if overwrite=true).
function copy_config(src::String, destpath::String,
                     destname::String=src, overwrite=true)
    mkpath(destpath)
    dest = joinpath(destpath, destname)
    srcbytes = rb(joinpath(Pkg.dir("IJulia"), "deps", src))
    if !isfile(dest) || (overwrite && !eqb(srcbytes, rb(dest)))
        eprintln("Copying $src to Julia IPython profile.")
        open(dest, "w") do f
            write(f, srcbytes)
        end
    else
        eprintln("(Existing $destname file untouched.)")
    end
end

# copy IJulia icon to profile so that IPython will use it
for T in ("png", "svg")
    copy_config("ijulialogo.$T",
                joinpath(juliaprof, "static", "base", "images"),
                "ipynblogo.$T")
end

# copy IJulia favicon to profile
copy_config("ijuliafavicon.ico",
            joinpath(juliaprof, "static", "base", "images"),
            "favicon.ico")

# custom.js can contain custom js login that will be loaded
# with the notebook to add info and/or monkey-patch some javascript
# -- e.g. we use it to add .ipynb metadata that this is a Julia notebook
copy_config("custom.js", joinpath(juliaprof, "static", "custom"))

# julia.js implements a CodeMirror mode for Julia syntax highlighting in the notebook.
# Eventually this will ship with CodeMirror and hence IPython, but for now we manually bundle it.

copy_config("julia.js", joinpath(juliaprof, "static", "components", "codemirror", "mode", "julia"))
