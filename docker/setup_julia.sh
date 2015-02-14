#!/bin/bash

DEFAULT_PACKAGES="IJulia PyPlot SIUnits Gadfly DataStructures HDF5 MAT \
Iterators NumericExtensions SymPy Interact Roots \
DataFrames RDatasets Distributions SVM Clustering GLM \
Optim JuMP GLPKMathProgInterface Clp NLopt Ipopt \
Cairo GraphViz \
Images ImageView WAV ODE Sundials LinearLeastSquares \
BayesNets PGFPlots GraphLayout \
Stan \
Patchwork Quandl Lazy QuantEcon"

for pkg in ${DEFAULT_PACKAGES}
do
    echo "Adding default package $pkg"
    julia -e "Pkg.add(\"$pkg\")"
done
