#include <cmath>
#include <iostream>
#include <vector>
#include <valarray>
#include <list>
#include <iterator>
#include <map>
#include <set>
#include <boost/graph/adjacency_list.hpp>
#include <boost/graph/connected_components.hpp>
#include <TTree.h>
#include <TFile.h>

#include <Clustering.h>

using namespace CLUSTERING;

struct Node {
  int status; // non-zero indicates this node is "good"
  int index;  // parameter space index for this node
  int i_hit; // hit index for this node
  int i_bco;
  int i_chan;
  int i_adc;

  Node(int i, int h, int b, int c, int a) :
    status(1), index(i), i_hit(h), i_bco(b), i_chan(c), i_adc(a)
  {}
  int getIndex() const { return i_hit; }
};

void
FindClusters(TTree* input_tree, TTree* output_tree)
{
  int hit, chan, adc, bco;
  if ( !input_tree )
    {
      std::cout << "FindClusters::Error: input tree does not exist!" << std::endl;
      return;
    } 
  input_tree->SetBranchAddress("hit",&hit);
  input_tree->SetBranchAddress("chan",&chan);
  input_tree->SetBranchAddress("adc",&adc);
  input_tree->SetBranchAddress("bco",&bco);

  std::vector<Node> nodes;
  std::map<int,int> index_map; // map of index in parameter space for each node in list

  int HIT_BINS = (int)input_tree->GetMaximum("hit");

  long nentries = input_tree->GetEntries();
  for( long ientry = 0; ientry < nentries; ientry++ )
    {
      input_tree->GetEntry(ientry);
      int index = hit*NBCO*NCHAN + bco*NCHAN + chan;
      nodes.push_back(Node(index,hit,bco,chan,adc));
      int in = nodes.size() - 1;
      index_map.insert(std::make_pair(index,in));
    }

  using namespace boost;
  typedef adjacency_list <vecS, vecS, undirectedS> Graph;
  typedef graph_traits<Graph>::vertex_descriptor Vertex;

  Graph G;
  int bco_window = 1;
  int hit_window = 1;
  int chan_window = 1;
  for( unsigned int i = 0; i < nodes.size(); i++ ) {
    int i_bco = nodes[i].i_bco;
    int i_chan = nodes[i].i_chan;
    int i_hit = nodes[i].i_hit;

    for( int ic = -1*chan_window; ic <= chan_window; ic++ )
      {
	for( int ih = -1*hit_window; ih <= hit_window; ih++ )
	  {
	    for( int ib = -1*bco_window; ib <= bco_window; ib++ )
	      {
		int b = i_bco + ib;
		int h = i_hit + ih;
		int c = i_chan + ic;

		// skip this index if goes outside parameter space
		if( h < 0 || h > HIT_BINS-1 ) continue;
		if( c < 0 || c > NCHAN-1 ) continue;
		// bco parameter is cycle so loop around if outside range
		if( b < 0 )
		  b = NBCO - b;
		if( b > NBCO-1 ) 
		  b = b - (NBCO - 1);

		int neighbor_index = h*NBCO*NCHAN + b*NCHAN + c;
		std::map<int,int>::const_iterator it = index_map.find(neighbor_index);
		if( it != index_map.end() )
		  {
		    int in = (*it).second;
		    //std::cout << "Connect index " << nodes[i].index << " to " << nodes[in].index << std::endl;
		    add_edge(i,in,G);
		  }
	      }
	  }
      }
  }

  std::vector<int> component(num_vertices(G));
  int num = connected_components(G, &component[0]);

  std::set<int> comps; // Number of unique components
  std::multimap<int,Node*> node_clusters;
  for( unsigned int i = 0; i < component.size(); i++ )
    {
      comps.insert(component[i]);
      node_clusters.insert(std::pair<int,Node*>(component[i],&nodes[i]));
    }

  std::cout << "num vertices = " << num_vertices(G) << " connected_comp = " << num << std::endl;

  int evnt = 0;
  int adc_sum = 0;
  int nhit = 0;
  float ch_rms = 0;
  float bco_rms = 0;
  int ch_w = 0;
  int bco_w = 0;
  int ch_id[5000];
  int ch_hit[5000];
  int ch_idx[5000];
  int ch_adc[5000];
  int ch_bco[5000];
  int ch_max = -1;
  int adc_max = -1;
  int bco_max = -1;
  int ch_high = -1;
  int ch_low = NCHAN;
  int bco_high = -1;
  int bco_low = NBCO;
  //TTree* event = new TTree("event","event");
  output_tree->Branch("evnt",&evnt,"evnt/I");
  output_tree->Branch("adc_sum",&adc_sum,"adc_sum/I");
  output_tree->Branch("nhit",&nhit,"nhit/I");
  output_tree->Branch("bco_rms",&bco_rms,"bco_rms/F");
  output_tree->Branch("ch_rms",&ch_rms,"ch_rms/F");
  output_tree->Branch("bco_w",&bco_w,"bco_w/I");
  output_tree->Branch("ch_w",&ch_w,"ch_w/I");
  output_tree->Branch("ch_id",ch_id,"ch_id[nhit]/I");
  output_tree->Branch("ch_hit",ch_hit,"ch_hit[nhit]/I");
  output_tree->Branch("ch_bco",ch_bco,"ch_bco[nhit]/I");
  output_tree->Branch("ch_adc",ch_adc,"ch_adc[nhit]/I");
  output_tree->Branch("ch_idx",ch_idx,"ch_idx[nhit]/I");

  std::map<int,Node*>::iterator b, e;
  for( std::set<int>::iterator i = comps.begin(); i!=comps.end(); i++ )
    {
      // Create "event" for each set of nodes in a cluster
      evnt = *i;
      boost::tie(b,e) = node_clusters.equal_range(*i);
      for( std::map<int,Node*>::iterator n = b; n != e; n++ )
	{
	  int hit, bco, chan, adc;
	  Node* n_p = n->second;
	  hit = n_p->i_hit;
	  bco = n_p->i_bco;
	  chan = n_p->i_chan;
	  adc = n_p->i_adc;
	  ch_hit[nhit] = hit;
	  ch_id[nhit] = chan;
	  ch_bco[nhit] = bco;
	  ch_adc[nhit] = adc+1;
	  adc_sum += adc+1;
	  if( chan > ch_high ) ch_high = chan;
	  if( chan < ch_low ) ch_low = chan;
	  if( bco > bco_high ) bco_high = bco;
	  if( bco < bco_low ) bco_low = bco;
	  if( adc > adc_max ) {
	    ch_max = chan;
	    adc_max = adc;
	    bco_max = bco;
	  }
	  nhit++;
	}

      for( int j = 0; j < nhit; j++ )
	{
	  ch_idx[j] = ch_max - ch_id[j];
	  //ch_w += ch_idx[j];
	  ch_rms += ch_idx[j]*ch_idx[j];
	  // bco cycles from 0 to 63 so delta_bco should reflect that
	  int delta_bco = abs(bco_max - ch_bco[j]);
	  if( delta_bco > NBCO/2 ) delta_bco = NBCO - delta_bco;
	  //bco_w += delta_bco;
	  bco_rms += delta_bco*delta_bco;
	}
      //ch_w = ch_id[nhit-1] - ch_id[0];
      ch_w = ch_high - ch_low;
      bco_w = bco_high - bco_low;
      if( bco_w > NBCO/2 ) bco_w = NBCO - bco_w;
      ch_rms = sqrt(ch_rms);
      bco_rms = sqrt(bco_rms);
      output_tree->Fill();

      // re-initialize event variables
      nhit = 0;
      adc_sum = 0;
      ch_w = 0;
      ch_high = -1;
      ch_low = NCHAN;
      bco_high = -1;
      bco_low = NBCO;
      bco_w = 0;
      ch_rms = 0;
      bco_rms = 0;
      ch_max = -1;
      adc_max = -1;
    }

}

