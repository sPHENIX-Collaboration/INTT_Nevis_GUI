#include <iostream>
#include <iomanip>
#include <set>
#include <vector>
#include <algorithm>

#include <TSystem.h>
#include <TROOT.h>
#include <TStyle.h>
#include <TCanvas.h>
#include <TH1F.h>
#include <TH2F.h>
#include <TTree.h>
#include <TFile.h>
#include <TPad.h>
#include <TText.h>
#if ROOT_VERSION_CODE >= ROOT_VERSION(5,26,0) 
#include <TTreePerfStats.h>
#endif

// zippyism:
// WHO sees a BEACH BUNNY sobbing on a SHAG RUG?!

void
find_bad_channels(TH1* h, double thresh, std::vector<int>& v)
{
  //double min = h->GetMinimum();
  double max = h->GetMaximum();
  int nx = h->GetXaxis()->GetNbins();
  for(int i=0; i<nx; i++)
    {
      double y = h->GetBinContent(i+1);
      if ( (max-y)/max > thresh )
	v.push_back(i);
    }
}

void
deadchannels(const char* fname, bool zerosuppress=true)
{
  // If a channel is missing more than this fraction of hits
  // it gets flagged.
  const double missing_thresh = 0.4;

  // Use uniform limits on the Y axes
  const double max_nhits = 4000.0;
  const double min_nhits = 0.0;

  TFile* f = new TFile(fname);
  if ( ! f->IsOpen() ) return;

  f->ls();
  f->cd();
  TTree* T = (TTree*)gROOT->FindObject("T");
  TTree* T1 = (TTree*)gROOT->FindObject("T1");

  if ( ! T ) {
    std::cout << "Failed to find T" << std::endl;
    return;
  }
  if ( ! T1 ) {
    std::cout << "Failed to find T1" << std::endl;
    return;
  }

  unsigned int runnumber;
  T1->SetBranchAddress("runnumber",&runnumber);
  T1->GetEntry(0);
  std::cout << "Run number " << runnumber << std::endl;

  // T is the tree containing the hits for the run
  //
  unsigned int word = 0;
  unsigned int bufcnt = 0;
  unsigned int datacnt = 0;
  unsigned short chan = 0;
  unsigned short amp = 0;
  unsigned short adc = 0;
  unsigned short bco = 0;
  unsigned short roc_chip_id = 0;
  unsigned short mod_chip_id = 0;
  unsigned short chip_id = 0;
  unsigned short side = 0;
  unsigned short fpga_id = 0;
  unsigned short module = 0;
  unsigned int hitcnt = 0;
  unsigned short last_word = 0;
  unsigned short fifo_full = 0;
  T->SetBranchStatus("*",0);
  //T->SetBranchAddress("buf",&datacnt,"buf/i");
  //T->SetBranchStatus("buf",1);
  //t->SetBranchAddress("hit",&hitcnt,"hit/i");
  T->SetBranchStatus("word",1);
  T->SetBranchAddress("word",&word); // uncomment for debugging
  T->SetBranchStatus("chan",1);
  T->SetBranchAddress("chan",&chan);
  T->SetBranchStatus("amp",1);
  T->SetBranchAddress("amp",&amp);
  //t->SetBranchAddress("adc",&adc,"adc/s");
  //t->SetBranchAddress("bco",&bco,"bco/s");
  T->SetBranchStatus("fpga",1);
  T->SetBranchAddress("fpga",&fpga_id);
  //t->SetBranchAddress("roc_chip",&roc_chip_id,"roc_chip/s");
  //t->SetBranchAddress("module",&module,"module/s");
  //t->SetBranchAddress("side",&side,"side/s");
  T->SetBranchStatus("chip",1);
  T->SetBranchAddress("chip",&chip_id);

  // Starting with 5.26, root implements much smarter reading
  // turn it on if we are using that version
  std::cout << "ROOT version " << ROOT_VERSION_CODE << std::endl;
#if ROOT_VERSION_CODE >= ROOT_VERSION(5,26,0) 
  std::cout << "using TTree cache"
	    << std::endl;
  TTreePerfStats *ps = new TTreePerfStats("ioperf",T);
  T->SetCacheSize(10000000);
  T->AddBranchToCache("*");
#endif

  TH1* hchan[2][14] = { { 0, 0 } };
  TH1* hAmpVsChan[2] = { 0, 0 };

  for (int n=0; n<2; n++)
    {
      char name[1024];
      char title[1024];
      sprintf(name,"hAmpVsChan_fpga%d",n);
      sprintf(title,"hAmpVsChan_fpga%d",n);
      hAmpVsChan[n] = new TH2F(name,title,13*128,-0.5,13*128-1,64,-0.5,63.5);
      for (int i=0; i<13; i++)
	{
	  sprintf(name,"hchan_fpga%d_chip%02d",n,i);
	  sprintf(title,"hchan_fpga%d_chip%02d",n,i);
	  hchan[n][i] = new TH1F(name,title,128,-0.5,127.5);
	}
    }

  std::set<int> chipids;
  int nentries = T->GetEntries();
  for (int i=0; i<nentries; i++)
    {
      T->GetEntry(i);
      if ( fpga_id > 1 ) // Can't be negative
  	{
  	  std::cout << "Entry " << i
  		    << ": packet 0x" << std::hex
  		    << word
  		    << std::dec
  		    << " Invalid FPGA id = " << fpga_id << std::endl;
  	  continue;
  	}
      if ( chip_id < 0 || chip_id > 13 )
  	{
  	  std::cout << "Entry " << i
  		    << ": packet 0x" << std::hex
  		    << word
  		    << std::dec
  		    << " Invalid chip id = " << chip_id << std::endl;
  	  continue;
  	}
      chipids.insert(chip_id);
      TH1* h = hchan[fpga_id][chip_id-1];
      if ( h )
  	{
  	  h->Fill(chan);
  	}
      TH1* h2 = hAmpVsChan[fpga_id];
      if ( h2 )
	{
	  int channel = -1;
	  if ( fpga_id == 0 )
	    {
	      channel = 127-chan + 128*(chip_id-1);
	    }
	  else
	    {
	      channel = chan + 128*(chip_id-1);
	    }
	  h2->Fill(channel,amp);
	}
    }

  std::cout << "Found " << chipids.size() << " different chip ids" << std::endl;

  TCanvas* c = new TCanvas(fname,fname);

  gStyle->SetPalette(1);
  gROOT->SetStyle("Plain");

  TPad* pad = new TPad("pad","pad",0.0,0.0,1.0,1.0);
  //pad->SetFillColor(2);
  pad->Draw();
  pad->cd();
  TText vlabel;
  vlabel.SetNDC(true);
  vlabel.SetTextAlign(22);
  vlabel.SetTextSize(0.05);
  vlabel.DrawText(0.5,0.95+0.05/2.0,"Chip by Chip Hit Distribution");
  vlabel.SetTextAngle(90.0);
  vlabel.DrawText(0.015,0.95/4.0*3.0,"Side 0");
  vlabel.DrawText(0.015,0.95/4.0*1.0,"Side 1");
  TPad* plots = new TPad("plots","plots",0.03,0.0,1.0,0.95);

  if ( chipids.size() < 6 )
    {
      plots->Divide(6,2,0.001,0.001);
    }
  else
    {
      plots->Divide(7,4,0.001,0.001);
    }
  plots->Draw();


  int max_chips = 13;
  if ( chipids.size() < 6 ) max_chips = 5;
  int ihist = 1;
  for (int i=0; i<2; i++)
    {
      // Try to discover the max hist value within the size, so we can normalize the axes to it
      std::set<double> max_vals;
      for (int j=0; j<max_chips; ++j)
	{
	  TH1* h = hchan[i][j];
	  if ( ! h ) continue;
	  double hmax = h->GetMaximum();
	  max_vals.insert(hmax);
	}
      double max_val = *(std::max_element(max_vals.begin(),max_vals.end()));

      for (int j=0; j<max_chips+1; j++)
	{
	  TVirtualPad* p = plots->cd(ihist++);
	  p->SetLeftMargin(0.23);
	  p->SetRightMargin(0.04);
	  TH1* h = 0;
	  if ( j < max_chips ) h = hchan[i][j];
	  else h = hAmpVsChan[i];

	  if ( h && j == max_chips )
	    {
	      // The 14th pad gets the 2-d hist of amp vs. channel
	      h->GetXaxis()->SetLabelSize(0.11);
	      h->GetYaxis()->SetLabelSize(0.11);
	      h->GetXaxis()->SetNdivisions(505);
	      h->GetXaxis()->SetRangeUser(-0.5,max_chips*128);
	      h->SetTitle("");
	      h->Draw("zcol");
	      char text[1024];
	      sprintf(text,"All Chips");
	      TText chtxt;
	      chtxt.SetNDC(true);
	      chtxt.SetTextSize(0.15);
	      chtxt.SetTextAlign(22);
	      chtxt.DrawText(p->GetLeftMargin()+(1-p->GetRightMargin()-p->GetLeftMargin())/2.0,0.95,text);
	    }
	  else if ( h && j != max_chips ) 
	    {
	      double hmin = h->GetMinimum();
	      double hmax = h->GetMaximum();
	      if ( hmax == 0 ) 
		{
		  std::cout << "Something wrong with hist " 
			    << h->GetName() << ": max = " << hmax
			    << std::endl;
		  continue;
		}
	      double frac_missing = (hmax-hmin)/hmax;
	      std::vector<int> bad_channels;
	      if ( frac_missing > missing_thresh )
		{
		  h->SetFillColor(kRed-9);
		  find_bad_channels(h,missing_thresh,bad_channels);
		}
	      else
		{
		  h->SetFillColor(kSpring-4);
		}
	      gStyle->SetOptStat(0);
	      //h->SetFillColor(10);
	      //h->SetFillStyle(1001);
	      h->GetXaxis()->SetLabelSize(0.11);
	      h->GetYaxis()->SetLabelSize(0.11);
	      h->GetXaxis()->SetNdivisions(505);
	      h->GetYaxis()->SetNdivisions(505);
	      h->SetMaximum(1.2*max_val);
	      //if ( (hmax < max_nhits) &&
	      //		   (max_nhits-hmax < 0.8*max_nhits) )
	      //	h->SetMaximum(max_nhits);
	      if ( ! zerosuppress ) h->SetMinimum(min_nhits);
	      h->SetTitle("");
	      h->Draw();
	      char text[1024];
	      sprintf(text,"Chip %d",j+1);
	      TText chtxt;
	      chtxt.SetNDC(true);
	      chtxt.SetTextSize(0.15);
	      chtxt.SetTextAlign(22);
	      chtxt.DrawText(p->GetLeftMargin()+(1-p->GetRightMargin()-p->GetLeftMargin())/2.0,0.95,text);
	      double x = 0.5;
	      double y = 0.65;
	      if ( bad_channels.size() > 20 )
		{
		  std::cout << "Chip id " << j+1 << ": "
			    << "Found " << bad_channels.size() 
			    << " bad channels.  Something is seriously wrong"
			    << std::endl;
		}
	      else
		{
		  for (unsigned int m=0; m<bad_channels.size(); m++)
		    {
		      std::cout << "Side " << i << " " 
				<< "Chip " << j+1 << ", channel " 
				<< bad_channels[m] << std::endl;
		      TText txt;
		      txt.SetNDC(true);
		      txt.SetTextSize(0.15);
		      txt.SetTextAlign(31);
		      char num[1024];
		      sprintf(num,"%3d",bad_channels[m]);
		      txt.DrawText(x,y,num);
		      y -= 0.1;
		    }
		}
	    }
	}
    }
  // Create an output file name for the plot which replaces "data"->"plots"
  // and ".root" with ".png".  addtionally strip out the odd "./" that
  // root sticks at the front of the path.
  TString fplot = fname;
  fplot.ReplaceAll("./","");
  fplot.ReplaceAll("data/","plots/");
  fplot.ReplaceAll(".root","_channel.png");
  c->SaveAs(fplot);

#if ROOT_VERSION_CODE >= ROOT_VERSION(5,26,0) 
  ps->SaveAs("perfstat.root");
#endif
}
