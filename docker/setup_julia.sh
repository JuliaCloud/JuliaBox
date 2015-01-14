#!/bin/bash

julia -e 'Pkg.init(); Pkg.add("IJulia"); Pkg.add("PyPlot"); Pkg.add("SIUnits"); Pkg.add("Gadfly"); Pkg.add("DataStructures"); Pkg.add("HDF5"); Pkg.add("MAT"); Pkg.add("Iterators"); Pkg.add("NumericExtensions"); Pkg.add("SymPy"); Pkg.add("Interact"); Pkg.add("Roots");'

julia -e 'Pkg.add("DataFrames"); Pkg.add("RDatasets"); Pkg.add("Distributions"); Pkg.add("SVM"); Pkg.add("Clustering"); Pkg.add("GLM");'

julia -e 'Pkg.add("Optim"); Pkg.add("JuMP"); Pkg.add("GLPKMathProgInterface"); Pkg.add("Clp"); Pkg.add("NLopt"); Pkg.add("Ipopt");'

julia -e 'Pkg.add("Cairo"); Pkg.add("GraphViz");'

julia -e 'Pkg.add("Images"); Pkg.add("ImageView"); Pkg.add("WAV"); Pkg.add("ODE"); Pkg.add("Sundials"); Pkg.add("LinearLeastSquares");'

julia -e 'Pkg.add("BayesNets"); Pkg.add("PGFPlots"); Pkg.add("GraphLayout");'

julia -e 'Pkg.add("Stan");'

julia -e 'Pkg.add("Patchwork"); Pkg.add("Quandl");'
