-- 19_allow_harp_exclusion_in_pd_target.sql
-- Lets pd_target record HARP refinances as excluded (S10, D-062) by adding
-- 'harp_refinance' to the allowed exclusion reasons. Replaces the CHECK
-- made in sql/13; sql/13 itself is not edited (D-048).
ALTER TABLE pd_target DROP CONSTRAINT pd_target_exclusion_reason_check;

ALTER TABLE pd_target ADD CONSTRAINT pd_target_exclusion_reason_check
    CHECK (exclusion_reason IN ('harp_refinance', 'no_performance', 'early_start',
                                'late_start', 'buyback_in_window', 'rpl_sale_in_window'));
