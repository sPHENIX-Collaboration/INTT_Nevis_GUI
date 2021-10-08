#include <iomanip>

void
plot_calib_raw(const char* fname="calib_adc_raw.root", bool nevis_cut=true)
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
  t->SetBranchAddress("hit",&hit);
  t->SetBranchAddress("chan",&chan);
  t->SetBranchAddress("amp",&amp);
  t->SetBranchAddress("adc",&adc);
  t->SetBranchAddress("bco",&bco);

  long nentries = t->GetEntries();
  t->GetEntry(nentries-1);
  hitcnt = hit;

  TH1* hbco = new TH1D("hbco","",64,-0.5,63.5);
  hbco->GetXaxis()->SetTitle("BCO (clock value)");
  TH1* hbco_cut = (TH1*) gROOT->FindObject("hbco_cut");
  if ( hbco_cut ) 
    {
      std::cout << "Found existing hist " << hbco_cut->GetName() << ", deleting" << std::endl;
      delete hbco_cut;
    }
  hbco_cut = (TH1*) hbco->Clone("hbco_cut");

  TH1* h = new TH2D("hampl","",128,-0.5,127.5,64,-0.5,63.5);
  h->GetXaxis()->SetTitle("Channel Number");
  h->GetYaxis()->SetTitle("Pulse Amplitude");

  TH1* h2 = new TH2D("h2","",64,-0.5,63.5,8,-0.5,7.5);
  h2->GetXaxis()->SetTitle("Pulse Amplitude");
  h2->GetYaxis()->SetTitle("ADC value");

  TH1* hh = new TH2F("hBcoChan","",128,-0.5,127.5,64,-0.5,63.5);
  hh->GetXaxis()->SetTitle("channel");
  hh->GetYaxis()->SetTitle("BCO");

  TH1* hevt = new TH2F("hHit","",500,0,hitcnt,128,-0.5,127.5);
  hevt->GetXaxis()->SetTitle("Hit Number");
  hevt->GetYaxis()->SetTitle("Channel");
  TH1* hevt_cut = (TH1*) gROOT->FindObject("hevt_cut");
  if ( hevt_cut ) 
    {
      std::cout << "Found existing hist " << hevt_cut->GetName() << ", deleting" << std::endl;
      delete hevt_cut;
    }
  hevt_cut = (TH1*) hevt->Clone("hevt_cut");

  TH1* hBcoHit = new TH2F("hBcoHit","",500,0,hitcnt,64,-0.5,63.5);
  hBcoHit->GetXaxis()->SetTitle("Hit Number");
  hBcoHit->GetYaxis()->SetTitle("BCO");
  

  // The Nevis chip has several really noisy channels.  Eric tells me that 
  // he requested the following channels be bonded out:
  //      16, 17, 47, 48, 70, 79, 96, and 127
  const int NUMBAD = 10;
  int noisyChan[NUMBAD] = { 0, 16, 17, 44, 47, 48, 70, 79, 96, 127 };
  char noisyStr[1000];
  for (int i=0; i<NUMBAD; i++)
    {
      if ( i == 0 ) sprintf(noisyStr,"(chan!=%d)",noisyChan[i]);
      else 
	sprintf(noisyStr,"%s&&(chan!=%d)",noisyStr,noisyChan[i]);
    }
  TCut exclChan = noisyStr;
  if ( ! nevis_cut ) exclChan = "1==1";
  std::cout << "Channel cut = " << exclChan.GetTitle() << std::endl;

  // Two bco dists: cut and uncut.  uncut is used to search for the real BCOs
  int nsel = t->Project(hbco->GetName(),"bco");
  std::cout << nsel << std::endl;
  nsel = t->Project(hbco_cut->GetName(),"bco",exclChan);
  std::cout << nsel << std::endl;

  int imax = hbco_cut->GetMaximumBin();
  int max_bco = hbco_cut->GetBinCenter(imax);
  std::cout << "Cut BCO dist max_bco = " << max_bco << std::endl;

  // Use TSpectrum to find peaks in the cut BCO spectrum
  TH1* ptr = hbco_cut;
  char peaksStr[1000];
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
	      if ( i == 0 ) sprintf(peaksStr,"(%d-2<=bco&&bco<=%d+2)",x,x);
	      else 
		sprintf(peaksStr,"%s||(%d-2<=bco&&bco<=%d+2)",peaksStr,x,x);
	    }
	}
      delete c1;
    }
  else std::cout << "Hist " << ptr->GetName() << " has no entries" << std::endl;
  TCut peaksCut = peaksStr;
  std::cout << "Peaks cut = " << peaksCut.GetTitle() << std::endl;

  char ss[100];
  sprintf(ss,"%d-2<=bco&&bco<=%d+2",max_bco,max_bco); // Select BCOmax + 1
  TCut cut = peaksCut;
  std::cout << "Applying cut " << cut.GetTitle() << std::endl;

  gROOT->SetStyle("Plain");
  gStyle->SetPalette(1);

  char cname[4000];
  char* p = gSystem->BaseName(fname);
  sprintf(cname,"calib_%s",p);
  TCanvas* c = new TCanvas(cname,cname,1200,800);
  c->Divide(3,2);

  c->cd(1);
  gPad->SetLogz();
  gPad->SetRightMargin(0.15);
  t->Project(hh->GetName(),"bco:chan","");
  hh->DrawCopy("zcol");
  TLatex l;
  l.SetNDC(true);
  l.DrawLatex(0.05,0.95,fname);

  c->cd(2);
  gPad->SetLogy();
  gStyle->SetOptStat(0);
  hbco->SetMinimum(0.9);
  hbco->DrawCopy();
  hbco_cut->SetLineColor(kBlue);
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
  TLegend* leg = new TLegend(0.4,0.7,0.85,0.9,0,"NDC");
  leg->SetFillStyle(0);
  leg->SetBorderSize(0.0);
  leg->AddEntry(hbco,"All channels","L");
  leg->AddEntry(hbco_cut,"Cut out noisy channels","L");
  leg->AddEntry(pm,"Peak search results","P");
  leg->Draw();

  c->cd(3);
  char buf[1000];
  sprintf(buf,"bco==%d",max_bco);
  TCut maxBco = buf;
  t->Project(hevt->GetName(),"chan:hit","");
  t->Project(hevt_cut->GetName(),"chan:hit",maxBco);
  hevt_cut->SetMarkerColor(kRed);
  hevt_cut->SetLineColor(kRed);
  hevt_cut->SetFillColor(kRed);
  hevt->DrawCopy();
  hevt_cut->DrawCopy("same");

  c->cd(4);
  t->Project(h2->GetName(),"adc:amp",cut&&exclChan);
  h2->DrawCopy("box");

  c->cd(5);
  //gPad->SetLogz();
  gPad->SetRightMargin(0.15);
  t->Project(hampl->GetName(),"amp:chan",cut&&exclChan);
  hampl->DrawCopy("zcol");

  c->cd(6);
  gPad->SetLogz();
  gPad->SetRightMargin(0.15);
  t->Project(hBcoHit->GetName(),"bco:hit");
  hBcoHit->DrawCopy("zcol");

  c->SaveAs(".png");
}
