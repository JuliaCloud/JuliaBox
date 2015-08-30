#!/bin/bash

julia -e 'Pkg.init()'

# Install packages for Julia stable
DEFAULT_PACKAGES="IJulia PyPlot SIUnits Gadfly DataStructures HDF5 MAT \
Iterators NumericExtensions SymPy Interact Roots \
DataFrames RDatasets Distributions SVM Clustering GLM \
Optim JuMP GLPKMathProgInterface Clp NLopt Ipopt \
Cairo GraphViz \
Images ImageView WAV ODE Sundials LinearLeastSquares \
BayesNets PGFPlots GraphLayout \
Stan Patchwork Quandl Lazy QuantEcon MixedModels Escher"

for pkg in ${DEFAULT_PACKAGES}
do
    echo ""
    echo "Adding default package $pkg to Julia stable"
    julia -e "Pkg.add(\"$pkg\")"
done

INTERNAL_PACKAGES="https://github.com/tanmaykm/JuliaBoxUtils.jl.git \
https://github.com/tanmaykm/JuliaWebAPI.jl.git \
https://github.com/shashi/Homework.jl.git"

for pkg in ${INTERNAL_PACKAGES}
do
    echo ""
    echo "Adding internal package $pkg to Julia stable"
    julia -e "Pkg.clone(\"$pkg\")"
done

if [[ $DEFAULT_PACKAGES == *" Interact "*]]
then
    echo "Checking out Interact package for IPython 3 compatibility"
    julia -e "Pkg.checkout(\"Interact\")"
fi

echo ""
echo "Creating Julia stable package list..."
julia -e 'println("JULIA_HOME: $JULIA_HOME\n"); versioninfo(); println(""); Pkg.status()' > /opt/julia_packages/stable_packages.txt
#echo ""
#echo "Running package tests..."
#julia -e "Pkg.test()" > /opt/julia_packages/packages_test_result.txt


/opt/julia_nightly/bin/julia -e 'Pkg.init()'

# Install packages for Julia nightly
JULIA_NIGHTLY_DEFAULT_PACKAGES="IJulia"

for pkg in ${JULIA_NIGHTLY_DEFAULT_PACKAGES}
do
    echo ""
    echo "Adding default package $pkg to Julia nightly"
    /opt/julia_nightly/bin/julia -e "Pkg.add(\"$pkg\")"
done

JULIA_NIGHTLY_INTERNAL_PACKAGES="https://github.com/tanmaykm/JuliaBoxUtils.jl.git \
https://github.com/tanmaykm/JuliaWebAPI.jl.git \
https://github.com/shashi/Homework.jl.git"

for pkg in ${JULIA_NIGHTLY_INTERNAL_PACKAGES}
do
    echo ""
    echo "Adding internal package $pkg to Julia nightly"
    /opt/julia_nightly/bin/julia -e "Pkg.clone(\"$pkg\")"
done

if [[ $JULIA_NIGHTLY_DEFAULT_PACKAGES == *" Interact "*]]
then
    echo "Checking out Interact package for IPython 3 compatibility"
    /opt/julia_nightly/bin/julia -e "Pkg.checkout(\"Interact\")"
fi

echo ""
echo "Creating Julia nightly package list..."
/opt/julia_nightly/bin/julia -e 'println("JULIA_HOME: $JULIA_HOME\n"); versioninfo(); println(""); Pkg.status()' > /opt/julia_packages/nightly_packages.txt
