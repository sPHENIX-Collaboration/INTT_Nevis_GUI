#include <cstdio>
#include <TFile.h>
#include <TTree.h>
#include <TPad.h>
#include <TH1F.h>
#include <iostream>
#include <TCanvas.h>
#include <TLegend.h>
//#include <iomanip>
#include <fstream>

#include <TString.h>
#include <TROOT.h>
#include <TMath.h>
#include <TF1.h>
#include <TGraph.h>
#include <TGraphErrors.h>

Double_t modErf_fixamp (Double_t *x, Double_t *p)
{
  Double_t fit_val = 100*0.5*( 1 + TMath::Erf( (x[0] - p[0]) / p[1] ) );
  return fit_val;
}

Double_t modErf (Double_t *x, Double_t *p)
{
  Double_t fit_val = p[2]*0.5*( 1 + TMath::Erf( (x[0] - p[0]) / p[1] ) );
  return fit_val;
}

void Wedge_QA_Fit(char * infname = "infname.root", const int VERBOSITY = 0, int NPULSES = 100, int NUMFPGA = 2, int NUMCHIP = 13, int NUMCHAN = 128)
{
  gROOT->Reset();
  ofstream Fit_Summary_file;
  ofstream Zero_Hits_file;
  Fit_Summary_file.open("Fit_Summary.list");
  Zero_Hits_file.open("Zero_Hit.list");

  TFile *f = TFile::Open(infname);
  TTree *T = (TTree *)f->Get("T");
  TTree *T1 = (TTree *)f->Get("T1");

  // T is the tree containing the hits for the run
  unsigned int word = 0;
  unsigned int datacnt = 0;
  unsigned short chan = 0;
  unsigned short amp = 0;
  unsigned short adc = 0;
  unsigned short bco = 0;
  unsigned short chip_id = 0;
  unsigned short side = 0;
  unsigned short fpga = 0;
  unsigned short module = 0;
  unsigned int hitcnt = 0;
  T->SetBranchAddress("buf",&datacnt);
  T->SetBranchAddress("hit",&hitcnt);
  T->SetBranchAddress("word",&word); // uncomment for debugging
  T->SetBranchAddress("chan",&chan);
  T->SetBranchAddress("amp",&amp);
  T->SetBranchAddress("adc",&adc);
  T->SetBranchAddress("bco",&bco);
  T->SetBranchAddress("fpga",&fpga);
  //T->SetBranchAddress("roc_chip",&roc_chip_id);
  T->SetBranchAddress("module",&module);
  T->SetBranchAddress("side",&side);
  T->SetBranchAddress("chip",&chip_id);

  // T1 is a tree containing the chip configuration for the run
  unsigned int runnumber = 0;
  unsigned short config_module = 0;
  unsigned short config_side = 0;
  unsigned short config_chip = 0;
  unsigned short enable_masks[8] = { 0 };
  char reg[16] = { '\0' }; 
  T1->SetBranchAddress("runnumber",&runnumber);
  T1->SetBranchAddress("module",&config_module);
  T1->SetBranchAddress("side",&config_side);
  T1->SetBranchAddress("chip",&config_chip);
  T1->SetBranchAddress("enable_masks",&enable_masks[0]);
  T1->SetBranchAddress("reg",&reg[0]);

  T1->GetEntry(0);



  TString outname = infname;
  outname.ReplaceAll(".root", "_calib.root");
  TFile *calibfile = new TFile(outname,"RECREATE");

  TH1F ***ph1fChan_Chip_amp = new TH1F** [NUMCHIP*NUMFPGA];
  for(int i=0;i<NUMCHIP*NUMFPGA;i++){ ph1fChan_Chip_amp[i] = new TH1F* [NUMCHAN];}

  for (int ichip = 0; ichip < NUMCHIP*NUMFPGA; ichip++) 
  {
    for (int ichan = 0; ichan < NUMCHAN; ichan++)
    { 
      TString name = "histo_chip_fpga"; name += ichip + 1 ; name += "_chan";  name += ichan;
      ph1fChan_Chip_amp[ichip][ichan] = new TH1F( name, name, 64, 0.0-0.5, 64.0-0.5);
      //ph1fChan_Chip_amp[ichip][ichan]->SetMarkerColor(2);
      //ph1fChan_Chip_amp[ichip][ichan]->SetMarkerStyle(8);
      //ph1fChan_Chip_amp[ichip][ichan]->SetMarkerSize(1);
      //ph1fChan_Chip_amp[ichip][ichan]->SetMinimum(-5);
    }	//for (int ichan = 0; ichan < NUMCHAN; ichan++)
  }  //for (int ichip = 0; ichip < NUMCHIP; ichip++)


  int  Tnentries = T->GetEntries();
  for(int ientry=0; ientry<Tnentries; ientry++)
  {
    T->GetEntry(ientry);
    ph1fChan_Chip_amp[NUMCHIP*fpga+chip_id - 1][chan]->Fill(amp);
  }

  TF1 *pmodErf_fit = new TF1("modErf_fit",modErf,0,63,3);
  TF1 *pfit_mean_fit = new TF1("fit_mean_fit","gaus(0)",30,63);
  TF1 *pfit_sigma_fit = new TF1("fit_sigma_fit","gaus(0)",0,20);
  TF1 *pfit_amp_fit = new TF1("fit_amp_fit","gaus(0)",95,105);
  char hist_name[1000];


  TH1F **pfit_mean = new TH1F* [NUMCHIP*NUMFPGA];
  TH1F **pfit_sigma = new TH1F* [NUMCHIP*NUMFPGA];
  TH1F **pfit_amp = new TH1F* [NUMCHIP*NUMFPGA];


  for(int i = 0; i<NUMCHIP*NUMFPGA; i++)
  {
    TString THist_name;
    //sprintf(hist_name,"Mean_distro_Run_%d_Chip_%d",runnumber,i);
    THist_name = "Mean_distro_Run_"; THist_name += runnumber; THist_name += "_Chip_"; THist_name += i+1;
    pfit_mean[i] = new TH1F(THist_name,THist_name,100,10,63);
    pfit_mean[i]->SetMaximum(40);
    //sprintf(hist_name,"Sigma_distro_Run_%d_Chip_%d",runnumber,i);
    THist_name = "Sigma_distro_Run_"; THist_name += runnumber; THist_name += "_Chip_"; THist_name += i+1;
    pfit_sigma[i] = new TH1F(THist_name,THist_name,100,0.0,10);
    pfit_sigma[i]->SetMaximum(40);
    //sprintf(hist_name,"Amp_distro_Run_%d_Chip_%d",runnumber,i);
    THist_name = "Amp_distro_Run_"; THist_name += runnumber; THist_name += "_Chip_"; THist_name += i+1;
    pfit_amp[i] = new TH1F(THist_name,THist_name,100,85,115);
    pfit_amp[i]->SetMaximum(100);
  }
  sprintf(hist_name,"Mean_distro_Run_%d",runnumber);
  TH1F *pfit_mean_summary = new TH1F(hist_name,hist_name,100,10,63);
  pfit_mean_summary->SetMaximum(1000);
  sprintf(hist_name,"Sigma_distro_Run_%d",runnumber);
  TH1F *pfit_sigma_summary = new TH1F(hist_name,hist_name,100,0.0,10);
  pfit_sigma_summary->SetMaximum(1000);
  sprintf(hist_name,"Amp_distro_Run_%d",runnumber);
  TH1F *pfit_amp_summary = new TH1F(hist_name,hist_name,100,85,115);
  pfit_amp_summary->SetMaximum(1000);
  // sprintf(hist_name,"Mean_Run_%d",runnumber);
  // TH1F *pmean = new TH1F(hist_name,hist_name,NUMCHAN*NUMCHIP,0,NUMCHAN*NUMCHIP);
  // sprintf(hist_name,"Sigma_Run_%d",runnumber);
  // TH1F *psigma = new TH1F(hist_name,hist_name,NUMCHAN*NUMCHIP,0,NUMCHAN*NUMCHIP);
  // sprintf(hist_name,"Amp_Run_%d",runnumber);
  // TH1F *pamp = new TH1F(hist_name,hist_name,NUMCHAN*NUMCHIP,0,NUMCHAN*NUMCHIP);

  float* Xaxis = new float [NUMFPGA*NUMCHIP*NUMCHAN];
  float* Xaxis_err = new float [NUMFPGA*NUMCHIP*NUMCHAN];
  float* TGamp = new float [NUMFPGA*NUMCHIP*NUMCHAN];
  float* TGamp_err = new float [NUMFPGA*NUMCHIP*NUMCHAN];
  float* TGsigma = new float [NUMFPGA*NUMCHIP*NUMCHAN];
  float* TGsigma_err = new float [NUMFPGA*NUMCHIP*NUMCHAN];
  float* TGmean = new float [NUMFPGA*NUMCHIP*NUMCHAN];
  float* TGmean_err = new float [NUMFPGA*NUMCHIP*NUMCHAN];


  for (int ichip = 0; ichip < NUMFPGA*NUMCHIP; ichip++)
    //for (int ichip = 0; ichip < 1; ichip++)
  {
    for (int ichan = 0; ichan < NUMCHAN; ichan++)
      //for (int ichan = 0; ichan < 1; ichan++)
    {
      pmodErf_fit->SetParameters(ph1fChan_Chip_amp[ichip][ichan]->GetMean(),ph1fChan_Chip_amp[ichip][ichan]->GetRMS(),100);
      pmodErf_fit->SetParNames("Mean","Sigma","Amp");
      ph1fChan_Chip_amp[ichip][ichan]->Fit("modErf_fit","Q");
      //Xaxis[ichan + ichip*NUMCHAN]=ichan + ichip*NUMCHAN;
      //Xaxis_err[ichan + ichip*NUMCHAN]=0;
      Xaxis[127-ichan + ichip*NUMCHAN]=ichan + ichip*NUMCHAN;
      Xaxis_err[127-ichan + ichip*NUMCHAN]=0;


      pfit_mean[ichip]->Fill(pmodErf_fit->GetParameter(0));
      pfit_mean_summary->Fill(pmodErf_fit->GetParameter(0));
      //pmean->SetBinContent( 1 + ichan + ichip*ichan,pmodErf_fit->GetParameter(0));
      TGmean[ichan + ichip*NUMCHAN]=pmodErf_fit->GetParameter(0);
      TGmean_err[ichan + ichip*NUMCHAN]=pmodErf_fit->GetParError(0);


      pfit_sigma[ichip]->Fill(pmodErf_fit->GetParameter(1));
      pfit_sigma_summary->Fill(pmodErf_fit->GetParameter(1));
      //psigma->SetBinContent( 1 + ichan + ichip*ichan,pmodErf_fit->GetParameter(1));
      TGsigma[ichan + ichip*NUMCHAN]=pmodErf_fit->GetParameter(1);
      TGsigma_err[ichan + ichip*NUMCHAN]=pmodErf_fit->GetParError(1);

      pfit_amp[ichip]->Fill(pmodErf_fit->GetParameter(2));
      pfit_amp_summary->Fill(pmodErf_fit->GetParameter(2));
      //pamp->SetBinContent( 1 + ichan + ichip*ichan,pmodErf_fit->GetParameter(2));
      TGamp[ichan + ichip*NUMCHAN]=pmodErf_fit->GetParameter(2);
      TGamp_err[ichan + ichip*NUMCHAN]=pmodErf_fit->GetParError(2);


      //Fill our summary file
      int hist_integral = ph1fChan_Chip_amp[ichip][ichan]->Integral();
      Fit_Summary_file << (ichip/NUMCHIP) << "\t" << (ichip%NUMCHIP) + 1 << "\t" << ichan << "\t" << hist_integral << "\t" << pmodErf_fit->GetParameter(0) << " +- " << pmodErf_fit->GetParError(0) << "\t" << pmodErf_fit->GetParameter(1)  << " +- " << pmodErf_fit->GetParError(1) << "\t" << pmodErf_fit->GetParameter(2) << " +- " << pmodErf_fit->GetParError(2) << endl;

      if(hist_integral <= 3){Zero_Hits_file << (ichip/NUMCHIP) << "\t" << (ichip%NUMCHIP) + 1 << "\t" << ichan << "\t" << hist_integral << endl;}
    }
  }

  TGraphErrors *pamp = new TGraphErrors(NUMFPGA*NUMCHIP*NUMCHAN,Xaxis,TGamp,Xaxis_err,TGamp_err);
  //TGraph *pamp = new TGraph(NUMCHIP*NUMCHAN,Xaxis,TGamp);
  sprintf(hist_name,"Amp_Run_%d",runnumber);
  pamp->SetTitle(hist_name);
  pamp->SetMinimum(90);
  pamp->SetMaximum(110);

  TGraphErrors *pmean = new TGraphErrors(NUMFPGA*NUMCHIP*NUMCHAN,Xaxis,TGmean,Xaxis_err,TGmean_err);
  //TGraph *pmean = new TGraph(NUMCHIP*NUMCHAN,Xaxis,TGmean);
  sprintf(hist_name,"Mean_Run_%d",runnumber);
  pmean->SetTitle(hist_name);
  pmean->SetMinimum(0);
  pmean->SetMaximum(64);


  TGraphErrors *psigma = new TGraphErrors(NUMFPGA*NUMCHIP*NUMCHAN,Xaxis,TGsigma,Xaxis_err,TGsigma_err);
  //TGraph *psigma = new TGraph(NUMCHIP*NUMCHAN,Xaxis,TGsigma);
  sprintf(hist_name,"Sigma_Run_%d",runnumber);
  psigma->SetTitle(hist_name);
  psigma->SetMinimum(0);
  psigma->SetMaximum(20);

  for (int ichip = 0; ichip < NUMCHIP*NUMFPGA; ichip++)
  { 
    if(ichip==0)
    {
      pfit_mean_fit->SetParameters(20,pfit_mean_summary->GetMean(),pfit_mean_summary->GetRMS());
      pfit_mean_fit->SetParNames("Amp","Mean","Sigma");
      pfit_sigma_fit->SetParameters(20,pfit_sigma_summary->GetMean(),pfit_sigma_summary->GetRMS());
      pfit_sigma_fit->SetParNames("Amp","Mean","Sigma");
      pfit_amp_fit->SetParameters(20,pfit_amp_summary->GetMean(),pfit_amp_summary->GetRMS());
      pfit_amp_fit->SetParNames("Amp","Mean","Sigma");
      pfit_mean_summary->Fit("fit_mean_fit");
      pfit_sigma_summary->Fit("fit_sigma_fit");
      pfit_amp_summary->Fit("fit_amp_fit");
    }

    pfit_mean_fit->SetParameters(20,pfit_mean[ichip]->GetMean(),pfit_mean[ichip]->GetRMS());
    pfit_mean_fit->SetParNames("Amp","Mean","Sigma");
    pfit_sigma_fit->SetParameters(20,pfit_sigma[ichip]->GetMean(),pfit_sigma[ichip]->GetRMS());
    pfit_sigma_fit->SetParNames("Amp","Mean","Sigma");
    pfit_amp_fit->SetParameters(20,pfit_amp[ichip]->GetMean(),pfit_amp[ichip]->GetRMS());
    pfit_amp_fit->SetParNames("Amp","Mean","Sigma");
    pfit_mean[ichip]->Fit("fit_mean_fit","Q");
    pfit_sigma[ichip]->Fit("fit_sigma_fit","Q");
    pfit_amp[ichip]->Fit("fit_amp_fit","Q");
  }
  TString Tcanname;
  TString Tcanfname;
  char cname[1000];


  for (int ichip = 0; ichip < NUMCHIP*NUMFPGA; ichip++)
  {
    if(ichip==0)
    {
      Tcanname = "Amp distro; Run="; Tcanname =+ runnumber; 
      sprintf(cname,"Amp_distro_Run_%d",runnumber);
      TCanvas *c1 = new TCanvas(cname, Tcanname);
      pfit_amp_summary->Draw();

      Tcanname = "Mean distro; Run="; Tcanname =+ runnumber;
      sprintf(cname,"Mean_distro_Run_%d",runnumber);
      TCanvas *c2 = new TCanvas(cname, Tcanname);
      pfit_mean_summary->Draw();

      Tcanname = "Sigma distro; Run="; Tcanname =+ runnumber;
      sprintf(cname,"Sigma_distro_Run_%d",runnumber);
      TCanvas *c3 = new TCanvas(cname, Tcanname);
      pfit_sigma_summary->Draw();

      if(VERBOSITY==1)
      {
	c1->SaveAs(".png");
	c2->SaveAs(".png");
	c3->SaveAs(".png");
      }
    }

    Tcanname = "Amp distro; Run="; Tcanname =+ runnumber; Tcanname =+ "; Chip="; Tcanname =+ ichip+1; 
    sprintf(cname,"Amp_distro_Run_%d_Chip_%d",runnumber,ichip+1);
    TCanvas *c1 = new TCanvas(cname, Tcanname);
    pfit_amp[ichip]->Draw();

    Tcanname = "Mean distro; Run="; Tcanname =+ runnumber; Tcanname =+ "; Chip="; Tcanname =+ ichip+1;
    sprintf(cname,"Mean_distro_Run_%d_Chip_%d",runnumber,ichip+1);
    TCanvas *c2 = new TCanvas(cname, Tcanname);
    pfit_mean[ichip]->Draw();

    Tcanname = "Sigma distro; Run="; Tcanname =+ runnumber; Tcanname =+ "; Chip="; Tcanname =+ ichip+1;
    sprintf(cname,"Sigma_distro_Run_%d_Chip_%d",runnumber,ichip+1);
    TCanvas *c3 = new TCanvas(cname, Tcanname);
    pfit_sigma[ichip]->Draw();

    if(VERBOSITY==1)
    {
      c1->SaveAs(".png");
      c2->SaveAs(".png");
      c3->SaveAs(".png");
    }
  }

  Tcanname = "Amp; Run="; Tcanname =+ runnumber;
  //Tcanfname = "Amp_distro_Run_"; Tcanfname =+ runnumber;
  sprintf(cname,"Amp_Run_%d",runnumber);
  TCanvas *c4 = new TCanvas(cname, Tcanname);
  pamp->Draw("AP");

  Tcanname = "Mean; Run="; Tcanname =+ runnumber;
  //Tcanfname = "Mean_distro_Run_"; Tcanfname =+ runnumber;
  sprintf(cname,"Mean_Run_%d",runnumber);
  //TCanvas *c2 = new TCanvas(Tcanfname, Tcanname);
  TCanvas *c5 = new TCanvas(cname, Tcanname);
  pmean->Draw("AP");

  Tcanname = "Sigma; Run="; Tcanname =+ runnumber;
  sprintf(cname,"Sigma_Run_%d",runnumber);
  TCanvas *c6 = new TCanvas(cname, Tcanname);
  psigma->Draw("AP");

  if(VERBOSITY==1)
  {
    c4->SaveAs(".png");
    c5->SaveAs(".png");
    c6->SaveAs(".png");
  }
  
  calibfile->Write();
  calibfile->Close();
  Fit_Summary_file.close();
  Zero_Hits_file.close();
}
