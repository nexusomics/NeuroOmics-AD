#!/usr/bin/env Rscript
# ==========================================================================
# limma differential-expression pipeline (standalone R version)
# Invoked by the rpy2 bridge when Bioconductor's limma is installed.
#
# Inputs (from caller): expr_mat (genes x samples), meta_df (with `sample`,
#   group columns), case_group, control_group, optional covariates `covs`.
# Output: data.frame(gene, log2fc, ave_expr, t, pvalue, fdr)
# ==========================================================================
suppressMessages({ library(limma) })

run_limma <- function(expr_mat, meta_df, case_group, control_group, group_col = "group", covs = character(0)) {
  meta_df <- as.data.frame(meta_df)
  rownames(meta_df) <- meta_df$sample
  samples <- intersect(colnames(expr_mat), rownames(meta_df))
  expr_mat <- expr_mat[, samples, drop = FALSE]
  meta_df <- meta_df[samples, , drop = FALSE]

  group <- factor(meta_df[[group_col]], levels = c(control_group, case_group))
  design <- model.matrix(~ group)
  colnames(design)[2] <- "case_vs_control"
  if (length(covs) > 0) {
    for (cv in covs) {
      if (cv %in% colnames(meta_df)) design <- cbind(design, meta_df[[cv]])
    }
  }

  fit <- lmFit(expr_mat, design)
  fit <- eBayes(fit)
  top <- topTable(fit, coef = "case_vs_control", number = Inf, sort.by = "none")
  data.frame(gene = rownames(top),
             log2fc = top$logFC,
             ave_expr = top$AveExpr,
             t = top$t,
             pvalue = top$P.Value,
             fdr = top$adj.P.Val,
             stringsAsFactors = FALSE)
}

# --- CLI mode (debugging / standalone use) -------------------------------
if (sys.nframe() == 0 && !interactive()) {
  args <- commandArgs(trailingOnly = TRUE)   # expr.csv meta.csv case control [out.csv]
  expr <- read.csv(args[1], row.names = 1, check.names = FALSE)
  meta <- read.csv(args[2], row.names = 1, check.names = FALSE)
  meta$sample <- rownames(meta)
  res <- run_limma(expr, meta, args[3], args[4])
  out <- if (length(args) >= 5) args[5] else "limma_results.csv"
  write.csv(res, out, row.names = FALSE)
  cat("wrote", nrow(res), "rows to", out, "\n")
}
