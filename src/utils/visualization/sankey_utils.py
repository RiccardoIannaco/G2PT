import matplotlib
import numpy as np


def factorize_genotype_attention(tree_parser, attention_mean_df, target_gene, weight, genotypes=('homozygous', 'heterozygous')):
    for snp in tree_parser.gene2snp[target_gene]:
        for genotype in genotypes:
            try:
                attention_mean_df.at[(target_gene, snp, genotype), 'Value'] *= weight
            except:
                continue
    return attention_mean_df


def factorize_attention_recursively(tree_parser, attention_mean_df, target, weight, direction='forward', genotypes=('homozygous', 'heterozygous')):
    for gene in tree_parser.sys2gene[target]:
        if direction == 'forward':
            module = 'gene2sys'
        else:
            module = 'sys2gene'
        attention_mean_df.at[(target, gene, module), 'Value']  *= weight
        if direction == 'forward':
            snp_weight = attention_mean_df.loc[(target, gene, module)]['Value']
            attention_mean_df = factorize_genotype_attention(tree_parser, attention_mean_df, gene, snp_weight, genotypes=genotypes)
    if len(tree_parser.sys_graph.out_edges(target))!=0:
        total_value = 0
        for node, child in tree_parser.sys_graph.out_edges(target):
            if direction == 'forward':
                module = 'sys2env'
            else:
                module = 'env2sys'
            attention_mean_df.at[(target, child, module), 'Value'] *= weight
            sys2env_value = attention_mean_df.loc[(target, child, module)]['Value']
            attention_mean_df = factorize_attention_recursively(tree_parser, attention_mean_df, child, sys2env_value, direction, genotypes=genotypes)
    return attention_mean_df


def make_all_column_names(tree_parser, target_gos, target_genes):
    """
    Build a single list of multi-index column names for:
      - SNP->Gene (homozygous & heterozygous)
      - Gene->Sys and Sys->Gene
      - Sys->Env and Env->Sys (based on the forward edges in the graph)

    Returns:
        A list of tuples: (direction, query, key, module)
    """
    column_names = []

    # 1) SNP->Gene (homo/heterozygous)
    for gene in target_genes:
        for snp in tree_parser.gene2snp[gene]:
            column_names.append(("forward", gene, snp, "homozygous"))
            column_names.append(("forward", gene, snp, "heterozygous"))

    # 2) Gene->Sys and Sys->Gene
    #    Only add columns if `gene` actually belongs to `go` in sys2gene
    for go in target_gos:
        for gene in target_genes:
            if gene in tree_parser.sys2gene[go]:
                # Gene->Sys
                column_names.append(("forward", go, gene, "gene2sys"))
                # Sys->Gene
                column_names.append(("backward", go, gene, "sys2gene"))

    all_paths = tree_parser.get_paths_from_node_to_leaves(tree_parser.sys_graph, target_gos[-1])
    all_edges_forward = tree_parser.get_edges_from_paths(all_paths)

    # 3) Sys->Env and Env->Sys
    #    Here we use the edges in `all_edges_forward`.
    #    Each edge is a (target, source) pair in the forward direction.
    #    You can adapt naming if you prefer a different tuple structure.
    for (query, key) in all_edges_forward:
        # forward
        column_names.append(("forward", query, key, "sys2env"))
        # backward
        column_names.append(("backward", query, key, "env2sys"))

    return column_names

def softmax(x):
    """Compute softmax values for each set of scores in x."""
    e_x = np.exp(x - np.max(x))
    return e_x / e_x.sum(axis=0)