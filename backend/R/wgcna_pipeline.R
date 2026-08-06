#!/usr/bin/env Rscript
# ==========================================================================
# WGCNA co-expression module detection (standalone / rpy2 bridge).
# Input: expression matrix (genes x samples). Output: gene->module table.
# ==========================================================================
suppressMessages({ library(WGCNA) })
options(stringsAsFactors = FALSE)

run_wgcna <- function(expr_mat, power = NULL, min_module_size = 20, merge_cut_height = 0.25) {
  datExpr <- t(expr_mat)  # WGCNA expects samples x genes
  gsg <- goodSamplesGenes(datExpr, verbose = 0)
  if (!gsg$allOK) datExpr <- datExpr[, gsg$goodGenes]

  if (is.null(power)) {
    sft <- pickSoftThreshold(datExpr, powerVector = c(seq(1, 10, by = 1), seq(12, 20, by = 2)), verbose = 0)
    power <- sft$powerEstimate
    if (is.na(power)) power <- 6
  }
  net <- blockwiseModules(datExpr, power = power, minModuleSize = min_module_size,
                          mergeCutHeight = merge_cut_height, numericLabels = TRUE,
                          networkType = "signed", verbose = 0)
  data.frame(gene = names(net$colors), module = as.integer(net$colors))
}

if (sys.nframe() == 0 && !interactive()) {
  args <- commandArgs(trailingOnly = TRUE)
  expr <- read.csv(args[1], row.names = 1, check.names = FALSE)
  res <- run_wgcna(expr)
  out <- if (length(args) >= 2) args[2] else "wgcna_modules.csv"
  write.csv(res, out, row.names = FALSE)
  cat("wrote", nrow(res), "gene-module assignments to", out, "\n")
}
