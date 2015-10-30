#!/bin/bash

function init_packages {
    JULIA_VER=$1
    /opt/julia-${JULIA_VER}/bin/julia -e "Pkg.init()"
}

function include_packages {
    JULIA_VER=$1
    PKG_LIST=$2
    METHOD=$3
    for PKG in $PKG_LIST
    do
        echo ""
        echo "$METHOD package $PKG to Julia $JULIA_VER ..."
        /opt/julia-${JULIA_VER}/bin/julia -e "Pkg.${METHOD}(\"$PKG\")"
    done
}

function list_packages {
    JULIA_VER=$1
    echo ""
    echo "Listing packages for Julia $JULIA_VER ..."
    /opt/julia-${JULIA_VER}/bin/julia -e 'println("JULIA_HOME: $JULIA_HOME\n"); versioninfo(); println(""); Pkg.status()' > /opt/julia_packages/julia-${JULIA_VER}.packages.txt
}

# Install packages for Julia 0.3
DEFAULT_PACKAGES="IJulia \
Gadfly PyPlot SIUnits DataStructures HDF5 MAT \
Iterators NumericExtensions SymPy Interact Roots \
DataFrames RDatasets Distributions SVM Clustering GLM \
Optim JuMP GLPKMathProgInterface Clp NLopt Ipopt \
Cairo GraphViz \
Images ImageView WAV ODE Sundials LinearLeastSquares \
BayesNets PGFPlots GraphLayout \
Stan Patchwork Quandl Lazy QuantEcon MixedModels Escher"

INTERNAL_PACKAGES="https://github.com/tanmaykm/JuliaBoxUtils.jl.git \
https://github.com/tanmaykm/JuliaWebAPI.jl.git \
https://github.com/shashi/Homework.jl.git"

init_packages "0.3"
include_packages "0.3" "$DEFAULT_PACKAGES" "add"
include_packages "0.3" "$INTERNAL_PACKAGES" "clone"
list_packages "0.3"

# Install packages for Julia 0.4 and 0.5
DEFAULT_PACKAGES="IJulia Requests DistributedArrays"

INTERNAL_PACKAGES="https://github.com/tanmaykm/JuliaBoxUtils.jl.git \
https://github.com/tanmaykm/JuliaWebAPI.jl.git \
https://github.com/gsd-ufal/CloudArray.jl.git \
https://github.com/shashi/Homework.jl.git"

for ver in 0.4 0.5
do
    init_packages "$ver"
    include_packages "$ver" "$DEFAULT_PACKAGES" "add"
    include_packages "$ver" "$INTERNAL_PACKAGES" "clone"
    list_packages "$ver"
done
