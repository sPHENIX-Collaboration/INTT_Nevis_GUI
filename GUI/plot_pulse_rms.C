TH2F* frame(const char* title,
            const int xbins, const double xmin, const double xmax,
            const int ybins, const double ymin, const double ymax,
            const char* xtitle, const char* ytitle)
{

  TH2F* myframe = new TH2F(title, title, xbins, xmin, xmax, ybins, ymin, ymax);

  myframe->SetStats(0);
  myframe->SetTitle("");
  myframe->SetXTitle(xtitle);
  myframe->SetYTitle(ytitle);

  myframe->GetXaxis()->SetTitleSize(0.06);
  myframe->GetXaxis()->SetTitleOffset(1.2);
  myframe->GetXaxis()->SetLabelSize(0.05);

  myframe->GetYaxis()->SetTitleSize(0.06);
  myframe->GetYaxis()->SetTitleOffset(1.1);
  myframe->GetYaxis()->SetLabelSize(0.05);

  myframe->Draw();

  return myframe;
}

void
plot_pulse_amp(const char* fname="calib_adc_raw.root",int amp = 0, int chan = 0, int par = 0, const char* par_name = "None")
{
  TFile* fin = new TFile(fname);
  if ( ! fin->IsOpen() ) 
    {
      std::cout << "Failed to open input file" << std::endl;
      delete fin;
      return;
    }

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

  std::ostringstream hbco_name;
  hbco_name << "hbco_recenter_" << chan << "_" << amp << "_" << par;
  TH1* hbco_recenter = (TH1*) gROOT->FindObject(hbco_name.str().c_str());
  if ( hbco_recenter ) 
    {
      std::cout << "Found existing hist " << hbco_recenter->GetName() << ", deleting" << std::endl;
      delete hbco_recenter;
    }
  hbco_recenter = (TH1*)hbco->Clone(hbco_name.str().c_str());
  std::ostringstream amp_title;
  amp_title << "Ch = " << chan << ", Amp = " << amp << ", " << par_name << " = " << par;
  hbco_recenter->SetTitle(amp_title.str().c_str());

  nsel = t->Project(hbco->GetName(),"bco");
  std::cout << nsel << std::endl;

  // Use TSpectrum to find peaks in the cut BCO spectrum
  TH1* ptr = hbco;
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
	    }
	}
      delete c1;
    }
  else std::cout << "Hist " << ptr->GetName() << " has no entries" << std::endl;

  std::ostringstream peak_shift;
  peak_shift << "(94.0 - " << pm->GetX()[0] << " + bco)%64";
  nsel = t->Project(hbco_recenter->GetName(),peak_shift.str().c_str());

  char cname[4000];
  char* p = gSystem->BaseName(fname);
  sprintf(cname,"rms_%s",p);
  TCanvas* c = new TCanvas(cname,cname,500,500);
  c->cd();
  gPad->SetLogy();

  hbco_recenter->SetStats(false);
  hbco_recenter->DrawCopy();
  std::ostringstream rms;
  rms << "Pulse RMS = " << hbco_recenter->GetRMS();
  TLatex txt;
  txt.SetNDC();
  txt.SetTextSize(0.03);
  txt.DrawLatex(0.6,0.8,rms.str().c_str());
  c->SaveAs(".png");
  TFile* fout = new TFile("pulse_rms_histos_270509.root","update");
  hbco_recenter->Write();
  fout->Close();
}

void plot_pulse_rms(const char* fname="pulse_rms_histos.root")
{
  TFile* fin = new TFile(fname);

  const int chan = 50;
  const int namp = 8;
  const int npar = 8;
  double pulse_rms[npar][namp];
  double amp[namp] = {30,40,50,60,70,80,90,100};
  int par[npar] = {0,2,4,6,8,10,12,15};
  TGraph* rms_graphs[npar];
  for( int ip = 0; ip < npar; ip++ )
    {
      for( int ia = 0; ia < namp; ia++ )
	{
	  std::ostringstream histo_name;
	  histo_name << "hbco_recenter_" << chan << "_" << amp[ia] << "_" << par[ip];
	  TH1* histo = fin->Get(histo_name.str().c_str());
	  if( !histo ) {
	    std::cout << "Macro Error: could not find " << histo_name.str() << std::endl;
	    pulse_rms[ip][ia] = 0.0;
	    continue;
	  }
	  histo->SetAxisRange(26,40,"X");
	  pulse_rms[ip][ia] = histo->GetRMS();
	}

      rms_graphs[ip] = new TGraph(namp,amp,pulse_rms[ip]);
    }

  TCanvas* c1 = new TCanvas("rms_plot","rms_plot");
  c1->cd();
  gPad->SetLogy();
  TH2F* rms_frame = (TH2F*)frame("",100,20.0,120.0,150,1e-2,5.0,"pulse amp","pulse BCO_{rms}");
  rms_frame->Draw();

  TLegend* leg = new TLegend(0.8,0.55,0.98,0.96);
  leg->SetFillColor(0);
  leg->SetMargin(0.2);
  leg->SetTextSize(0.03);
  leg->SetEntrySeparation(0.4);

  for( int ip = 0; ip < npar; ip++ )
    {
      std::ostringstream leg_name;
      leg_name << "  N2Sel = " << par[ip];
      rms_graphs[ip]->SetMarkerColor(ip%4+1);
      rms_graphs[ip]->SetMarkerStyle(20+npar-ip-1);
      rms_graphs[ip]->SetMarkerSize(1.2);
      rms_graphs[ip]->Draw("P");
      leg->AddEntry(rms_graphs[ip],leg_name.str().c_str(),"P");
    }
  leg->Draw();
  c1->SaveAs(".png");
}
