#!/bin/bash

DEFAULT_PACKAGES="IJulia PyPlot SIUnits Gadfly DataStructures HDF5 MAT \
Iterators NumericExtensions SymPy Interact Roots \
DataFrames RDatasets Distributions SVM Clustering GLM \
Optim JuMP GLPKMathProgInterface Clp NLopt Ipopt \
Cairo GraphViz \
Images ImageView WAV ODE Sundials LinearLeastSquares \
BayesNets PGFPlots GraphLayout \
Stan Patchwork Quandl Lazy QuantEcon MixedModels"

for pkg in ${DEFAULT_PACKAGES}
do
    echo ""
    echo "Adding default package $pkg"
    julia -e "Pkg.add(\"$pkg\")"
done

INTERNAL_PACKAGES="https://github.com/shashi/Homework.jl.git \
https://github.com/tanmaykm/JuliaBox.jl.git"

for pkg in ${INTERNAL_PACKAGES}
do
    echo ""
    echo "Adding internal package $pkg"
    julia -e "Pkg.clone(\"$pkg\")"
done

julia -e "Pkg.checkout(\"Interact\")"

echo ""
echo "Creating package list..."
julia -e "Pkg.status()" > /home/juser/.juliabox/packages.txt
#echo ""
#echo "Running package tests..."
#julia -e "Pkg.test()" > /home/juser/.juliabox/packages_test_result.txt
