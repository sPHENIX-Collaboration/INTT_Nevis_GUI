#include <iostream>
#include <iomanip>
#include <set>
#include <vector>
#include <algorithm>

#include <TROOT.h>
#include <TStyle.h>
#include <TCanvas.h>
#include <TH1F.h>
#include <TH2F.h>
#include <TTree.h>
#include <TFile.h>
#include <TPad.h>
#include <TText.h>
#include <TF1.h>
#if ROOT_VERSION_CODE >= ROOT_VERSION(5,26,0) 
#include <TTreePerfStats.h>
#endif

void
sourcetest(const char* fname,     // input file name
	   bool zerosuppress=true // plot with zero suppressed
	   )
{
#ifdef __CINT__
  std::cout << "Please compile this code with .C+ or .C++ and try again" << std::endl;
  return;
#endif

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
  //t->SetBranchAddress("amp",&amp,"amp/s");
  T->SetBranchStatus("adc",1);
  T->SetBranchAddress("adc",&adc);
  T->SetBranchStatus("bco",1);
  T->SetBranchAddress("bco",&bco);
  T->SetBranchStatus("fpga",1);
  T->SetBranchAddress("fpga",&fpga_id);
  //t->SetBranchAddress("roc_chip",&roc_chip_id,"roc_chip/s");
  //t->SetBranchAddress("module",&module,"module/s");
  //t->SetBranchAddress("side",&side,"side/s");
  T->SetBranchStatus("chip",1);
  T->SetBranchAddress("chip",&chip_id);

  int max_chipid = T->GetMaximum("chip");
  int totalchan = 1664;
  if ( max_chipid == 5 )
    {
      totalchan = max_chipid*128;
    }

  TH1* hside[2] = { 0, 0 };
  TH1* hadc[2] = { 0, 0 };
  TH1* hbco[2] = { 0, 0 };
  for (int n=0; n<2; n++)
    {
      char name[1024];
      char title[1024];
      sprintf(name,"hside_fpga%d",n);
      sprintf(title,"hside_fpga%d",n);
      hside[n] = new TH1F(name,title,totalchan,-0.5,totalchan-0.5);
      sprintf(name,"hadcside_fpga%d",n);
      sprintf(title,"hadc_fpga%d",n);
      hadc[n] = new TH1F(name,title,8,-0.5,7.5);
      sprintf(name,"hbco_fpga%d",n);
      sprintf(title,"hbco_fpga%d",n);
      hbco[n] = new TH1F(name,title,128,-0.5,127.5);
    }

  int nentries = T->GetEntries();
  for (int i=0; i<nentries; i++)
    {
      T->GetEntry(i);
      if ( fpga_id > 1 || fpga_id < 0 )
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
      TH1* h = hside[fpga_id];
      if ( h )
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
	  h->Fill(channel);
	}
      TH1* h2 = hadc[fpga_id];
      if ( h2 )
  	{
	  h2->Fill(adc);
	}
      TH1* h3 = hbco[fpga_id];
      if ( h3 )
  	{
	  h3->Fill(bco);
	}
    }

  TCanvas* c = new TCanvas(fname,fname);
  TPad* pad = new TPad("pad","pad",0.0,0.0,1.0,1.0);
  pad->Draw();
  pad->cd();
  TText vlabel;
  vlabel.SetNDC(true);
  vlabel.SetTextAlign(22);
  vlabel.SetTextSize(0.05);
  vlabel.DrawText(0.5,0.95+0.05/2.0,"Source Test Distributions");
  vlabel.SetTextAngle(90.0);
  vlabel.DrawText(0.015,0.95/4.0*3.0,"Side 0");
  vlabel.DrawText(0.015,0.95/4.0*1.0,"Side 1");
  TPad* plots = new TPad("plots","plots",0.03,0.0,(1.0-0.03)*0.33,0.95);
  plots->Divide(1,2,0.0001,0.0001);
  plots->Draw();
  TPad* plots2 = new TPad("plots2","plots2",1.0-(1.0-0.03)*0.66,0.0,1.0-(1.0-0.03)*0.33,0.95);
  plots2->Divide(1,2,0.0001,0.0001);
  plots2->Draw();
  TPad* plots3 = new TPad("plots3","plots3",1.0-(1.0-0.03)*0.33,0.0,1.0,0.95);
  plots3->Divide(1,2);
  plots3->Draw();

  int ihist = 1;
  TF1* fcn = new TF1("fcn","gausn(0)+pol1(3)",0.0,1664.0);
  fcn->SetLineColor(2);
  for (int i=0; i<2; i++)
    {
      TVirtualPad* p = plots->cd(ihist++);
      p->SetLeftMargin(0.15);
      p->SetRightMargin(0.05);
      p->SetLogy();
      TH1* h = hside[i];
      if ( h ) 
	{
	  if ( 0 )
	    {
	      h->SetFillColor(kRed-9);
	    }
	  else
	    {
	      h->SetFillColor(kSpring-4);
	    }
	  h->GetXaxis()->SetLabelSize(0.1);
	  h->GetYaxis()->SetLabelSize(0.1);
	  h->GetXaxis()->SetNdivisions(505);
	  char title[1024];
	  sprintf(title,"Side %d Hits",i);
	  h->SetTitle("");
	  h->Draw();
	  fcn->SetParameter(0,h->GetEntries()); // Constant
	  fcn->SetParameter(1,800.0); // Mean
	  fcn->SetParameter(2,300.0); // Sigma
	  h->Fit(fcn);
	  char text[1024];
	  sprintf(text,"Hits");
	  TText chtxt;
	  chtxt.SetNDC(true);
	  chtxt.SetTextSize(0.11);
	  chtxt.SetTextAlign(22);
	  chtxt.DrawText(p->GetLeftMargin()+(1-p->GetRightMargin()-p->GetLeftMargin())/2.0,0.95,text);
	}
    }

  ihist = 1;
  for (int i=0; i<2; i++)
    {
      TVirtualPad* p = plots2->cd(ihist++);
      p->SetLeftMargin(0.2);
      p->SetRightMargin(0.05);
      //TH1* h = hadc[i];
      TH1* h = hbco[i];
      if ( h ) 
	{
	  h->GetXaxis()->SetLabelSize(0.08);
	  h->GetYaxis()->SetLabelSize(0.08);
	  h->GetXaxis()->SetNdivisions(505);
	  if ( ! zerosuppress ) h->SetMinimum(0.0);
	  char title[1024];
	  sprintf(title,"Side %d BCO",i);
	  h->SetTitle("");
	  h->Draw();
	  char text[1024];
	  sprintf(text,"BCO");
	  TText chtxt;
	  chtxt.SetNDC(true);
	  chtxt.SetTextSize(0.11);
	  chtxt.SetTextAlign(22);
	  chtxt.DrawText(p->GetLeftMargin()+(1-p->GetRightMargin()-p->GetLeftMargin())/2.0,0.95,text);
	}
    }
  ihist = 1;
  for (int i=0; i<2; i++)
    {
      TVirtualPad* p = plots3->cd(ihist++);
      p->SetLeftMargin(0.2);
      p->SetRightMargin(0.05);
      TH1* h = hadc[i];
      if ( h ) 
	{
	  h->GetXaxis()->SetLabelSize(0.08);
	  h->GetYaxis()->SetLabelSize(0.08);
	  h->GetXaxis()->SetNdivisions(505);
	  h->GetYaxis()->SetNdivisions(505);
	  if ( ! zerosuppress ) h->SetMinimum(0.0);
	  char title[1024];
	  sprintf(title,"Side %d ADC",i);
	  h->SetTitle("");
	  h->Draw();
	  char text[1024];
	  sprintf(text,"ADC");
	  TText chtxt;
	  chtxt.SetNDC(true);
	  chtxt.SetTextSize(0.11);
	  chtxt.SetTextAlign(22);
	  chtxt.DrawText(p->GetLeftMargin()+(1-p->GetRightMargin()-p->GetLeftMargin())/2.0,0.95,text);
	}
    }
  // Create an output file name for the plot which replaces "data"->"plots"
  // and ".root" with ".png".  addtionally strip out the odd "./" that
  // root sticks at the front of the path.
  TString fplot = fname;
  fplot.ReplaceAll("./","");
  fplot.ReplaceAll("data/","plots/");
  fplot.ReplaceAll(".root","_source.png");
  c->SaveAs(fplot);
}
