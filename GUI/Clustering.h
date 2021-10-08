#ifndef __CLUSTERING_H__
#define __CLUSTERING_H__

class TTree;

void FindClusters(TTree* input_tree, TTree* output_tree);

namespace CLUSTERING
{
  static const int NBCO = 64;
  static const int NCHAN = 128;
  static const int ADC_MAX = 8;
}

#endif
