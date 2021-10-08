#include <Clustering.h>
#include <TFile.h>
#include <TTree.h>
#include <iostream>

//void
//get_raw_events(const char* fname="calib_adc_raw.root", const char* oname="raw_events.root")

int main(int argc, char **argv)
{
  //gSystem->Load("libtest_clustering.so");
  //std::cout << gSystem->DynamicPathName("libtest_clustering.so") << std::endl;

  std::string fname = "calib_adc_raw.root";
  if( argv[1] ) fname = std::string(argv[1]);
  TFile* fin = new TFile(fname.c_str());
  if ( ! fin->IsOpen() ) 
    {
      std::cout << "Failed to open input file" << std::endl;
      delete fin;
      return 1;
    }

  TTree* t = (TTree*)fin->Get("t");
  if ( !t )
    {
      std::cout << "Failed to find TTree " << t->GetName() << std::endl;
      delete t;
      delete fin;
      return 1;
    }

  std::string oname = "raw_events.root";
  if( argv[2] ) oname = std::string(argv[2]);
  TFile* fout = new TFile(oname.c_str(),"recreate");
  TTree* event = new TTree("event","event");

  FindClusters(t,event);
  event->Write();
  fout->Close();

  return 0;
}
