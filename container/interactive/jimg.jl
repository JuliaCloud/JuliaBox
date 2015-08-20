if Pkg.installed("Gadfly") != nothing
	include(joinpath(Pkg.dir("Gadfly"), "src/Gadfly.jl"))
	importall Gadfly
end
