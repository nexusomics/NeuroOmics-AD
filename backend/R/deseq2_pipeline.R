#!/usr/bin/env Rscript
# ==========================================================================
# DESeq2 differential-expression pipeline for raw count matrices.
# Invoked by the rpy2 bridge when DESeq2 is installed.
# Output: data.frame(gene, log2fc, baseMean, stat, pvalue, fdr)
# ==========================================================================
suppressMessages({ library(DESeq2) })

run_deseq2 <- function(count_mat, meta_df, case_group, control_group, group_col = "group", covs = character(0)) {
  meta_df <- as.data.frame(meta_df)
  rownames(meta_df) <- meta_df$sample
  samples <- intersect(colnames(count_mat), rownames(meta_df))
  count_mat <- round(count_mat[, samples, drop = FALSE])
  meta_df <- meta_df[samples, , drop = FALSE]
  meta_df[[group_col]] <- relevel(factor(meta_df[[group_col]]), ref = control_group)

  design_formula <- as.formula(paste("~", paste(c(covs, group_col), collapse = " + ")))
  dds <- DESeqDataSetFromMatrix(countData = count_mat, colData = meta_df, design = design_formula)
  dds <- DESeq(dds, quiet = TRUE)
  res <- results(dds, contrast = c(group_col, case_group, control_group))
  data.frame(gene = rownames(res),
             log2fc = res$log2FoldChange,
             base_mean = res$baseMean,
             stat = res$stat,
             pvalue = res$pvalue,
             fdr = res$padj,
             stringsAsFactors = FALSE)
}

if (sys.nframe() == 0 && !interactive()) {
  args <- commandArgs(trailingOnly = TRUE)
  counts <- read.csv(args[1], row.names = 1, check.names = FALSE)
  meta <- read.csv(args[2], row.names = 1, check.names = FALSE)
  meta$sample <- rownames(meta)
  res <- run_deseq2(counts, meta, args[3], args[4])
  out <- if (length(args) >= 5) args[5] else "deseq2_results.csv"
  write.csv(res, out, row.names = FALSE)
  cat("wrote", nrow(res), "rows to", out, "\n")
}
