# Credit Risk Portfolio Methodology

> This document defines portfolio-wide principles. The Master Credit Risk Portfolio Prompt is the governing specification; project-specific requirements and justified methodological decisions take precedence over generic rules here.

## 1. Data Integrity

- Never assume dataset column names, data types, formats, or meanings.
- Inspect the actual data before designing transformations or models.
- For new datasets, document:
  - `df.head(10)`
  - `df.info()`
  - `df.describe()`
  - relevant data periods/vintages
  - missingness and duplicates
  - target definition and event rate
- Preserve the distinction between raw, interim, processed, and external data.
- Do not modify original source data.

## 2. Prediction-Time Information

- Every feature must be available at the model's prediction/reference date.
- Explicitly investigate target leakage, look-ahead bias, post-outcome information, and inappropriate future information.
- Any feature whose availability is uncertain must be investigated before use.

## 3. Data Splitting & Validation

- Choose train/validation/test methodology according to the data-generating process and project objective.
- Use temporal or out-of-time validation when appropriate for credit-risk applications.
- Do not use information from validation or test data during model development.
- The final test set should remain untouched until final evaluation.
- Any resampling, feature selection, imputation, or transformation that can learn from data must be fitted using training data only.

## 4. Reproducibility

- Use `RANDOM_STATE = 42` wherever applicable.
- Record important assumptions, transformations, hyperparameters, and model versions.
- Ensure important analytical results can be reproduced from documented code and data inputs.

## 5. Class Imbalance

- Measure and report the actual event/default rate before selecting an imbalance strategy.
- Do not automatically apply SMOTE, undersampling, weighting, or other resampling methods.
- If resampling is used, apply it only within the training process and evaluate whether it improves the relevant risk metrics.

## 6. Credit Risk Modeling

Where relevant, distinguish clearly between:

- PD — Probability of Default
- LGD — Loss Given Default
- EAD — Exposure at Default
- ECL — Expected Credit Loss

For scorecard/PD work, evaluate appropriate techniques such as:

- binning
- WOE
- IV
- logistic regression
- score scaling
- characteristic analysis

Use these techniques when appropriate rather than treating them as mandatory for every model.

## 7. Model Evaluation

Use metrics appropriate to the model and business problem.

Potential metrics include:

- ROC-AUC
- PR-AUC
- KS
- Gini
- Log Loss
- Brier Score
- calibration measures
- confusion-matrix metrics
- lift/gain
- business/risk metrics

Accuracy should not be treated as the primary metric for rare-event credit-risk problems.

Evaluate both **discrimination and calibration** where applicable.

## 8. Stability & Robustness

Where appropriate, evaluate:

- out-of-time performance
- population stability
- feature stability
- segment performance
- sensitivity to assumptions
- performance degradation
- drift

Do not declare a model robust based only on a single test-set metric.

## 9. Explainability

Use explainability methods appropriate to the model, such as:

- WOE/IV
- model coefficients
- feature importance
- SHAP
- partial dependence or related diagnostics

Explainability results must correspond to the actual fitted model and actual data.

## 10. Model Validation & Governance

Document, where applicable:

- model purpose
- target definition
- population
- data sources
- assumptions
- methodology
- feature selection
- validation methodology
- performance
- calibration
- stability
- limitations
- known model risks
- monitoring considerations

Apply relevant principles from established credit-risk/model-risk frameworks, including Basel, IFRS 9/CECL, SR 11-7, and applicable regulatory guidance, according to the specific project and jurisdiction.

Do not claim regulatory compliance merely because a project references a framework.

## 11. Transparency

- Never fabricate data, results, model performance, validation results, or business conclusions.
- Clearly distinguish observed results from assumptions, estimates, and illustrative examples.
- Record important methodological decisions and explain why they were made.
- Prefer evidence-driven decisions over arbitrary modeling conventions.

## 12. Cross-Project Consistency

Projects should use consistent:

- naming conventions
- random-state conventions
- data-handling principles
- validation philosophy
- documentation standards
- model evaluation principles

However, consistency must not override a project-specific methodological requirement.

Each project should clearly document deviations from the portfolio-wide standards when justified.
