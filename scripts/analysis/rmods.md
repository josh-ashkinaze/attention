Models
================
Joshua Ashkinaze
2023-03-28

# Load packages

## Load Data

``` r
##############################################
# LOAD DATA
##############################################
# read in data
df <- read_csv("https://raw.githubusercontent.com/josh-ashkinaze/attention/main/data/trend_merged_data_modeling.csv")
```

    ## New names:
    ## Rows: 16314 Columns: 24
    ## ── Column specification
    ## ──────────────────────────────────────────────────────── Delimiter: "," chr
    ## (6): search_type, event, kw, index, kwe, period dbl (13): ...1, value,
    ## rumor_delta, announce_delta, rumor_announce_gap, stu... date (5): date,
    ## rumor_day, announce_day, max_date, min_date
    ## ℹ Use `spec()` to retrieve the full column specification for this data. ℹ
    ## Specify the column types or set `show_col_types = FALSE` to quiet this message.
    ## • `` -> `...1`

``` r
df$year <- year(df$date)
df$month <- month(df$date)
df$week <- week(df$date)

# kwid is unique kw-id: (event, keyword, search_type)
df$kwid <- paste(paste(df$kw, df$event, "_"), df$search_type, "_")

# kwe is (keyword, event)
df$kwe <- paste(paste(df$kw, df$event, "_"))
                
df$search_type <- factor(df$search_type)
df$search_type <- relevel(df$search_type, ref = "web")
df$period <- factor(df$period)
df$period <- relevel(df$period, "control")
df$kw <- as.factor(df$kw)
df$event <- as.factor(df$event)
df$log_val <- log(df$value+1)
```

# Modeling

Note: Point estimates are the same between

``` r
##############################################
# RANDOM FX 
##############################################
# Make mixed model 
model.crossed <- lmer(value ~ start_delta + year + month + period*search_type + (1 | kw) + (1|event), data = df)
```

    ## boundary (singular) fit: see help('isSingular')

``` r
model.nested <- lmer(value ~ start_delta + year + month + period*search_type + (1 | event/kw), data = df)

##############################################
# PANEL MODEL VERSION
##############################################
# Fit the fixed effects model and then get newey west standard errors
fem <- plm(value ~ period * search_type, data = df, model = "within", index = c("kwe", "date", "search_type"))
```

    ## Warning in pdata.frame(data, index): duplicate couples (id-time) in resulting pdata.frame
    ##  to find out which, use, e.g., table(index(your_pdataframe), useNA = "ifany")

``` r
fixed_ses <- summary(fem, vcov = vcovNW)
fem_robust_se <- fixed_ses$coefficients[, 2]
fem_p_values <- fixed_ses$coefficients[, 4]


##############################################
# LOOK AT/PLOT CONTRASTS
##############################################
# Look at contrasts: 
# For rumors, is attention higher for google news and YT vs web?
# For announcements, is attention higher for web vs google news and YT?
em <- emmeans(model.nested, ~ period*search_type)
```

    ## Note: D.f. calculations have been disabled because the number of observations exceeds 3000.
    ## To enable adjustments, add the argument 'pbkrtest.limit = 16314' (or larger)
    ## [or, globally, 'set emm_options(pbkrtest.limit = 16314)' or larger];
    ## but be warned that this may result in large computation time and memory use.

    ## Note: D.f. calculations have been disabled because the number of observations exceeds 3000.
    ## To enable adjustments, add the argument 'lmerTest.limit = 16314' (or larger)
    ## [or, globally, 'set emm_options(lmerTest.limit = 16314)' or larger];
    ## but be warned that this may result in large computation time and memory use.

``` r
em_df <- as.data.frame(em)
pairs <- pairs(em, by = "period", type = "response", rev = TRUE)
print(pairs)
```

    ## period = control:
    ##  contrast              estimate    SE  df z.ratio p.value
    ##  google_news - web        2.620 0.345 Inf   7.603  <.0001
    ##  youtube - web            2.846 0.345 Inf   8.258  <.0001
    ##  youtube - google_news    0.226 0.345 Inf   0.656  0.7891
    ## 
    ## period = announce_period:
    ##  contrast              estimate    SE  df z.ratio p.value
    ##  google_news - web      -27.031 3.139 Inf  -8.610  <.0001
    ##  youtube - web          -32.844 3.139 Inf -10.462  <.0001
    ##  youtube - google_news   -5.812 3.139 Inf  -1.851  0.1531
    ## 
    ## period = rumor_period:
    ##  contrast              estimate    SE  df z.ratio p.value
    ##  google_news - web       12.844 3.139 Inf   4.091  0.0001
    ##  youtube - web           11.938 3.139 Inf   3.802  0.0004
    ##  youtube - google_news   -0.906 3.139 Inf  -0.289  0.9551
    ## 
    ## Degrees-of-freedom method: asymptotic 
    ## P value adjustment: tukey method for comparing a family of 3 estimates

``` r
# Let's graph the Search Type X Period emmeans
em_df$lower <- em_df$asymp.LCL
em_df$upper <- em_df$asymp.UCL
ggplot(data=data.frame(em_df), aes(x=period, y=emmean, fill=search_type, ymin=lower, ymax=upper)) + 
  geom_bar(stat="identity", position=position_dodge(width=0.9)) +
  geom_errorbar(position=position_dodge(width=0.9), width=0.2) +
  labs(x="Period", y="Normalized Attention (0-100)", fill="Search type", title="People are more likely to turn to the web during announcements\nand more likely to turn to platforms during rumors.", subtitle="Data from Google Trends.\nPoint estimates and 95% CIs are marginal means from mixed effects model.") + theme_nice() + scale_fill_manual(values = hex_color_list)
```

![](rmods_files/figure-gfm/mixed_linar-1.png)<!-- -->

``` r
##############################################
# DISPLAY MODELS
##############################################
models <- list(model.crossed, model.nested, fem)
model_names <- c("Crossed", 
                 "Nested", 
                 "Fixed Effect Model\n(Newey West Clustered Errors)")

stargazer(models, 
          dep.var.labels = c("Normalized Attention"),
          model.names = TRUE,
          column.labels = model_names, 
          type = 'latex', 
          se = list(NULL, NULL, fem_robust_se), 
          p = list(NULL, NULL, fem_p_values))
```

    ## 
    ## % Table created by stargazer v.5.2.3 by Marek Hlavac, Social Policy Institute. E-mail: marek.hlavac at gmail.com
    ## % Date and time: Mon, Jun 19, 2023 - 11:26:44
    ## \begin{table}[!htbp] \centering 
    ##   \caption{} 
    ##   \label{} 
    ## \begin{tabular}{@{\extracolsep{5pt}}lccc} 
    ## \\[-1.8ex]\hline 
    ## \hline \\[-1.8ex] 
    ##  & \multicolumn{3}{c}{\textit{Dependent variable:}} \\ 
    ## \cline{2-4} 
    ## \\[-1.8ex] & \multicolumn{3}{c}{Normalized Attention} \\ 
    ## \\[-1.8ex] & \multicolumn{2}{c}{\textit{linear}} & \textit{panel} \\ 
    ##  & \multicolumn{2}{c}{\textit{mixed-effects}} & \textit{linear} \\ 
    ##  & Crossed & Nested & Fixed Effect Model
    ## (Newey West Clustered Errors) \\ 
    ## \\[-1.8ex] & (1) & (2) & (3)\\ 
    ## \hline \\[-1.8ex] 
    ##  start\_delta & 0.059$^{***}$ & 0.058$^{***}$ &  \\ 
    ##   & (0.006) & (0.006) &  \\ 
    ##   & & & \\ 
    ##  year & 1.475$^{**}$ & 1.949$^{**}$ &  \\ 
    ##   & (0.719) & (0.981) &  \\ 
    ##   & & & \\ 
    ##  month & $-$0.094 & $-$0.058 &  \\ 
    ##   & (0.081) & (0.099) &  \\ 
    ##   & & & \\ 
    ##  periodannounce\_period & 57.762$^{***}$ & 57.758$^{***}$ & 58.520$^{***}$ \\ 
    ##   & (2.234) & (2.234) & (4.610) \\ 
    ##   & & & \\ 
    ##  periodrumor\_period & 2.658 & 2.659 & 1.895 \\ 
    ##   & (2.234) & (2.234) & (2.561) \\ 
    ##   & & & \\ 
    ##  search\_typegoogle\_news & 2.620$^{***}$ & 2.620$^{***}$ & 2.620$^{***}$ \\ 
    ##   & (0.345) & (0.345) & (0.413) \\ 
    ##   & & & \\ 
    ##  search\_typeyoutube & 2.846$^{***}$ & 2.846$^{***}$ & 2.846$^{***}$ \\ 
    ##   & (0.345) & (0.345) & (0.414) \\ 
    ##   & & & \\ 
    ##  periodannounce\_period:search\_typegoogle\_news & $-$29.652$^{***}$ & $-$29.652$^{***}$ & $-$29.652$^{***}$ \\ 
    ##   & (3.158) & (3.158) & (6.439) \\ 
    ##   & & & \\ 
    ##  periodrumor\_period:search\_typegoogle\_news & 10.223$^{***}$ & 10.223$^{***}$ & 10.223$^{**}$ \\ 
    ##   & (3.158) & (3.158) & (4.696) \\ 
    ##   & & & \\ 
    ##  periodannounce\_period:search\_typeyoutube & $-$35.690$^{***}$ & $-$35.690$^{***}$ & $-$35.690$^{***}$ \\ 
    ##   & (3.158) & (3.158) & (6.232) \\ 
    ##   & & & \\ 
    ##  periodrumor\_period:search\_typeyoutube & 9.091$^{***}$ & 9.091$^{***}$ & 9.091$^{**}$ \\ 
    ##   & (3.158) & (3.158) & (4.602) \\ 
    ##   & & & \\ 
    ##  Constant & $-$2,971.032$^{**}$ & $-$3,928.704$^{**}$ &  \\ 
    ##   & (1,451.359) & (1,979.393) &  \\ 
    ##   & & & \\ 
    ## \hline \\[-1.8ex] 
    ## Observations & 16,314 & 16,314 & 16,314 \\ 
    ## R$^{2}$ &  &  & 0.062 \\ 
    ## Adjusted R$^{2}$ &  &  & 0.058 \\ 
    ## Log Likelihood & $-$70,178.520 & $-$70,195.290 &  \\ 
    ## Akaike Inf. Crit. & 140,387.000 & 140,420.600 &  \\ 
    ## Bayesian Inf. Crit. & 140,502.500 & 140,536.100 &  \\ 
    ## F Statistic &  &  & 133.648$^{***}$ (df = 8; 16242) \\ 
    ## \hline 
    ## \hline \\[-1.8ex] 
    ## \textit{Note:}  & \multicolumn{3}{r}{$^{*}$p$<$0.1; $^{**}$p$<$0.05; $^{***}$p$<$0.01} \\ 
    ## \end{tabular} 
    ## \end{table}
