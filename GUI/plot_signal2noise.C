double sin_func(double* x, double* par)
{
  double func;
  func = par[0]*TMath::Sin(par[1]*x[0]+par[2]) + par[3];
  if( x[0] > 27 && x[0] < 29 )
    TF1::RejectPoint();
  return func;
}

void
plot_signal2noise(const char* fname="calib_adc_raw.root",const char* amp_title="Channel 1: Amp = 1 BCO = 63")
{
  TFile* fin = new TFile(fname);
  if ( ! fin->IsOpen() ) 
    {
      std::cout << "Failed to open input file" << std::endl;
      delete fin;
      return;
    }

  int hit, chan, amp, adc, bco;
  int hitcnt = 0;
  TTree* t = (TTree*)fin->Get("t");
  if ( !t )
    {
      std::cout << "Failed to find TTree " << t->GetName() << std::endl;
      delete t;
      delete fin;
      return;
    } 

  TH1* hbco = new TH1D("hbco","",64,-0.5,63.5);
  hbco->GetXaxis()->SetTitle("BCO (clock value)");
  TH1* hbco_cut = (TH1*) gROOT->FindObject("hbco_cut");
  if ( hbco_cut ) 
    {
      std::cout << "Found existing hist " << hbco_cut->GetName() << ", deleting" << std::endl;
      delete hbco_cut;
    }
  hbco_cut = (TH1*) hbco->Clone("hbco_cut");
  TH1* hbco_signal = (TH1*) gROOT->FindObject("hbco_signal");
  if ( hbco_signal ) 
    {
      std::cout << "Found existing hist " << hbco_signal->GetName() << ", deleting" << std::endl;
      delete hbco_signal;
    }
  TH1* hbco_max_channel = (TH1*) gROOT->FindObject("hbco_max_channel");
  if ( hbco_max_channel ) 
    {
      std::cout << "Found existing hist " << hbco_max_channel->GetName() << ", deleting" << std::endl;
      delete hbco_max_channel;
    }
  hbco_max_channel = (TH1*)hbco->Clone("hbco_max_channel");
  TH1* hbco_recenter = (TH1*) gROOT->FindObject("hbco_recenter");
  if ( hbco_recenter ) 
    {
      std::cout << "Found existing hist " << hbco_recenter->GetName() << ", deleting" << std::endl;
      delete hbco_recenter;
    }
  hbco_recenter = (TH1*)hbco->Clone("hbco_recenter");
  hbco_recenter->SetTitle(amp_title);

  int nsel = t->Project(hbco->GetName(),"bco");
  std::cout << nsel << std::endl;
  hbco_signal = (TH1*) hbco->Clone("hbco_signal");

  TH2* hh = new TH2F("hBcoChan","",128,-0.5,127.5,64,-0.5,63.5);
  hh->GetXaxis()->SetTitle("channel");
  hh->GetYaxis()->SetTitle("BCO");

  TH1* hchannel = new TH1D("hchannel","",128,-0.5,127.5);
  hchannel->GetXaxis()->SetTitle("channel");

  // Use TSpectrum to find peaks in the cut BCO spectrum
  TH1* ptr = hbco;
  char peaksStr[1000];
  char bgStr[1000];
  TPolyMarker* pm = 0;
  if ( ptr->GetEntries() != 0 ) 
    {
      // TSpectrum stupidly executes a Draw() in the process of 
      // its algorthim.  We create a dummy canvas to allow to do its work w/o
      // messing up any of our canvases.
      TCanvas* c1 = new TCanvas();
      
      gSystem->Load("libSpectrum");
      TSpectrum sp;
      int npeaks = sp.Search(ptr,1,"nobackground");
      std::cout << "TSpectrum found " << npeaks << " peaks" << std::endl;
      TList* fcns = ptr->GetListOfFunctions();
      pm = (TPolyMarker*)fcns->FindObject("TPolyMarker");
      if ( pm )
	{
	  for (int i=0; i<npeaks; i++)
	    {
	      double x = pm->GetX()[i];
	      std::cout << "Peak " << i << " X = " << x << std::endl;
	      if ( i == 0 ) {
		sprintf(peaksStr,"(%d-2<=bco&&bco<=%d+4)",x,x);
		sprintf(bgStr,"!(%d-2<=bco&&bco<=%d+4)",x,x);
	      }
	      else {
		sprintf(peaksStr,"%s||(%d<=bco&&bco<=%d+1)",peaksStr,x,x);
		sprintf(bgStr,"%s||!(%d<=bco&&bco<=%d+1)",peaksStr,x,x);
	      }
	    }
	}
      delete c1;
    }
  else std::cout << "Hist " << ptr->GetName() << " has no entries" << std::endl;
  TCut peaksCut = peaksStr;
  TCut bgCut = bgStr;
  std::cout << "Peaks cut = " << peaksCut.GetTitle() << std::endl;

  nsel = t->Project(hbco_cut->GetName(),"bco",bgCut);
  std::cout << nsel << std::endl;

  std::ostringstream peak_shift;
  peak_shift << "(94.0 - " << pm->GetX()[0] << " + bco)%64";
  nsel = t->Project(hbco_recenter->GetName(),peak_shift.str().c_str());

  gROOT->SetStyle("Plain");
  gStyle->SetOptFit(1111);
  gStyle->SetPalette(1);

  char cname[4000];
  char* p = gSystem->BaseName(fname);
  sprintf(cname,"calib_%s",p);
  TCanvas* c = new TCanvas(cname,cname,1000,500);
  c->Divide(3,1);

  c->cd(1);
  //gPad->SetRightMargin(0.15);
  gPad->SetLogy();
  hbco_recenter->DrawCopy();

  c->cd(2);
  gPad->SetLogy();
  gStyle->SetOptStat(0);
  //TF1* fit = new TF1("fit","[0]*sin([1]*x+[2])+[3]",0,63);
  TF1* fit = new TF1("fit",sin_func,0,63,4);
  fit->SetParameters(100,1/63.0,50,350);
  fit->SetParNames("amp","freq","phase","bg");
  hbco_cut->Fit("fit","R");

  hbco_signal->Add(fit,-1.0);
  int bin_low = hbco_signal->FindBin(pm->GetX()[0]);
  int bin_high = hbco_signal->FindBin(pm->GetX()[0]+3.0);
  double signal = hbco_signal->Integral(bin_low,bin_high);
  double background = fit->Integral(pm->GetX()[0],pm->GetX()[0]+3.0);
  double sb_ratio = 0.0;
  if( background ) sb_ratio = signal/background;
  std::ostringstream S_B_string;
  S_B_string << "Peak S/B = " << sb_ratio;
  std::cout << "signal/background = " << signal << "/" << background << " = " << sb_ratio << std::endl;

  hbco->SetMinimum(0.9);
  hbco->DrawCopy();
  hbco_cut->SetLineColor(kBlue);
  hbco_cut->SetStats(false);
  hbco_cut->DrawCopy("same");
  if ( pm )
    {
      for (int i=0; i<pm->GetN(); i++)
	{
	  double x = pm->GetX()[i];
	  double y = pm->GetY()[i];
	  char s[10];
	  sprintf(s,"%d",x);
	  TLatex txt;
	  txt.SetTextAlign(21);
	  txt.DrawLatex(x,2.0*y,s); // 2x b/c it's a log-y plot
	}
    }
  TLegend* leg = new TLegend(0.54,0.83,0.99,0.99,0,"NDC");
  //leg->SetFillStyle(0);
  leg->SetBorderSize(0.0);
  leg->SetTextSize(0.04);
  leg->AddEntry(hbco,"All channels","L");
  leg->AddEntry(hbco_cut,"Cut out pulse peak","L");
  leg->AddEntry(pm,S_B_string.str().c_str(),"P");
  //leg->AddEntry(hbco,S_B_string.str().c_str(),"P");
  leg->Draw();

  c->cd(3);
  gPad->SetLogy();
  gStyle->SetOptStat(0);
  hbco_cut->SetStats(true);
  hbco_cut->SetTitle("Noise fit");
  hbco_cut->DrawCopy();
  TLegend* leg2 = new TLegend(0.2,0.75,0.65,0.95,0,"NDC");
  leg2->SetFillStyle(0);
  leg2->SetBorderSize(0.0);
  leg2->SetTextSize(0.04);
  leg2->AddEntry(fit,"A*sin(#omega*x+#phi)+bg","L");
  leg2->Draw();

  char pname[4000];
  char* p = gSystem->BaseName(fname);
  sprintf(pname,"sb_calib_%s.png",p);
  c->SaveAs(pname);

  /*
  t->Project(hh->GetName(),"bco:chan",bgCut);
  t->Project(hchannel->GetName(),"chan",bgCut);

  c->cd(3);
  gPad->SetRightMargin(0.15);
  hh->FitSlicesY(fit,0,-1,0,"R");
  TH1D* hh_chi2 = (TH1D*)gDirectory->Get("hBcoChan_chi2");
  hh_chi2->SetTitle("");
  hh_chi2->GetYaxis()->SetTitle("chisquare");
  hh_chi2->Draw();

  TH1D* chi2_dist = new TH1D("chi2_dist","",50,0.0,2.0);
  chi2_dist->GetXaxis()->SetTitle("chisquare");
  for( int ibin = 1; ibin <= hh_chi2->GetNbinsX(); ibin++ )
    {
      chi2_dist->Fill(hh_chi2->GetBinContent(ibin));
    }

  c->cd(4);
  gPad->SetRightMargin(0.15);
  chi2_dist->Draw();

  double max_channel = hchannel->GetMaximumBin();
  std::cout << "max channel = " << max_channel << std::endl;
  char noisyStr[1000];
  sprintf(noisyStr,"(chan==%d)",max_channel-1);
  TCut selectChan = noisyStr;
  t->Project(hbco_max_channel->GetName(),"bco",selectChan);
  //hbco_max_channel->DrawCopy();
  */
}
