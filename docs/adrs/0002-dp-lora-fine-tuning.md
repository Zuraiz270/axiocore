# ADR 0002: DP-LoRA for Privacy-Preserving Fine-Tuning

**Date:** 2026-03-16
**Status:** Accepted

## Context
Axiocore aims to be a self-improving system. To achieve this, it must use human review corrections to fine-tune its underlying models. However, standard fine-tuning on sensitive document data (invoices, medical records) poses a high risk of model inversion attacks, where PII might be memorized and later reconstructed from model weights.

## Decision
We will implement **Differential Privacy (DP)** during the fine-tuning process using the **Opacus** library in conjunction with **PEFT (LoRA)**.
1. **LoRA (Low-Rank Adaptation):** Minimizes the number of trainable parameters, reducing the "memorization surface" and lowering compute requirements.
2. **Opacus:** Injects calibrated noise into the gradients and clips them during backpropagation to provide formal $(\epsilon, \delta)$-differential privacy guarantees.

## Consequences
**Positive:**
- Provides a mathematical guarantee that individual training records cannot be reconstructed from the model.
- Enables "Flywheel" learning across tenants without violating data residency or privacy contracts.
- Low GPU memory footprint due to LoRA.

**Negative:**
- **Utility Trade-off:** DP noise can slow down convergence or slightly reduce the accuracy of the fine-tuned model compared to non-private tuning.
- **Privacy Budget Management:** Requires tracking $\epsilon$ consumption; once the budget is exhausted, the model cannot be further fine-tuned on that specific dataset.
