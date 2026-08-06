#!/usr/bin/env Rscript
# ==========================================================================
# Cross-cohort meta-analysis (R reference implementation using metafor).
# Combine per-cohort effect sizes with fixed/random effects.
# ==========================================================================
suppressMessages({ library(metafor) })

run_meta <- function(effect_dfs, fixed_effects = TRUE) {
  # effect_dfs: list of data.frames(gene, effect, var)
  genes <- unique(unlist(lapply(effect_dfs, function(d) d$gene)))
  out <- do.call(rbind, lapply(genes, function(g) {
    rows <- lapply(effect_dfs, function(d) d[d$gene == g, ])
    es <- sapply(rows, function(r) if (nrow(r)) r$effect else NA_real_)
    vs <- sapply(rows, function(r) if (nrow(r)) r$var else NA_real_)
    ok <- !is.na(es) & !is.na(vs) & vs > 0
    if (sum(ok) == 0) return(NULL)
    res <- rma(yi = es[ok], vi = vs[ok], method = if (fixed_effects) "FE" else "DL")
    data.frame(gene = g, pooled_effect = res$b[1, 1], se = res$se,
               pvalue = res$pval, i2_percent = ifelse(is.null(res$I2), NA, res$I2),
               n_cohorts = sum(ok), stringsAsFactors = FALSE)
  }))
  out$fdr <- p.adjust(out$pvalue, method = "BH")
  out[order(out$pvalue), ]
}

if (sys.nframe() == 0 && !interactive()) {
  args <- commandArgs(trailingOnly = TRUE)
  files <- args[1:(length(args) - 1)]
  dfs <- lapply(files, read.csv)
  res <- run_meta(dfs)
  write.csv(res, args[length(args)], row.names = FALSE)
  cat("wrote", nrow(res), "rows\n")
}
