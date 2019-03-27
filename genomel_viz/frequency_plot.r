library(ggplot2)
test=read.table('stacked_frequency.csv', sep=',',header=F)
names(test) <- c('index','genotype', 'ratio')
ggplot(test, aes(x=ratio, fill=genotype)) + geom_density(alpha=.9)