
void
plot_clusters(const char* fname="raw_events.root")
{
  TFile* fin = new TFile(fname);
  if ( ! fin->IsOpen() ) 
    {
      std::cout << "Failed to open input file" << std::endl;
      delete fin;
      return;
    }

  int nhit, evnt, adc_sum, bco_w, ch_w;
  float bco_rms, ch_rms;
  int ch_id[2000];
  int ch_hit[2000];
  int ch_idx[2000];
  int ch_adc[2000];
  int ch_bco[2000];
  int hitcnt = 0;
  int adcmax = 0;
  int chmax = 0;
  int hitmax = 0;
  int bcomax = 0;
  TTree* t = (TTree*)fin->Get("event");
  if ( !t )
    {
      std::cout << "Failed to find TTree " << t->GetName() << std::endl;
      delete t;
      delete fin;
      return;
    } 
  hitcnt = t->GetMaximum("ch_hit");
  adcmax = t->GetMaximum("adc_sum");
  chmax = t->GetMaximum("ch_w");
  bcomax = t->GetMaximum("bco_w");
  hitmax = t->GetMaximum("nhit");
  t->SetBranchAddress("evnt",&evnt);
  t->SetBranchAddress("adc_sum",&adc_sum);
  t->SetBranchAddress("nhit",&nhit);
  t->SetBranchAddress("bco_rms",&bco_rms);
  t->SetBranchAddress("ch_rms",&ch_rms);
  t->SetBranchAddress("bco_w",&bco_w);
  t->SetBranchAddress("ch_w",&ch_w);
  t->SetBranchAddress("ch_hit",ch_hit);
  t->SetBranchAddress("ch_id",ch_id);
  t->SetBranchAddress("ch_idx",ch_idx);
  t->SetBranchAddress("ch_adc",ch_adc);
  t->SetBranchAddress("ch_bco",ch_bco);

  double ch_rms_max = t->GetMaximum("ch_rms")/(double)hitmax;
  double bco_rms_max = t->GetMaximum("bco_rms")/(double)hitmax;
  TH1* hdedx = new TH1F("hdEdx","",20,-0.5,19.5);
  hdedx->Sumw2();
  hdedx->GetXaxis()->SetTitle("|#Delta ch|");
  hdedx->GetYaxis()->SetTitle("adc");

  TH1* hclst = new TH1F("hCluster","",39,-19.5,19.5);
  hclst->Sumw2();
  hclst->GetXaxis()->SetTitle("#Delta ch = ch_{i} - ch_{max}");
  //hclst->GetYaxis()->SetTitle("adc");
  TH1* hclst_cut = hclst->Clone("hCluster_cut");

  TH1* hadc = new TH1F("hADC","",adcmax+1,-0.5,adcmax+0.5);
  hadc->Sumw2();
  hadc->GetXaxis()->SetTitle("adc_{total}");
  TH1* hadc_cut = hadc->Clone("hADC_cut");

  TH1* have = new TH1F("hAveADC","",10,-0.5,9.5);
  have->Sumw2();
  have->GetXaxis()->SetTitle("<adc>");
  TH1* have_cut = have->Clone("hAveADC_cut");

  TH1* hcw = new TH1F("hChWidth","",int((ch_rms_max+0.3)*20),0.2,ch_rms_max+0.5);
  hcw->Sumw2();
  hcw->GetXaxis()->SetTitle("ch_{rms}");
  TH1* hcw_cut = hcw->Clone("hChWidth_cut");

  TH1* hbw = new TH1F("hBcoWidth","",int((bco_rms_max+0.6)*15),-0.1,bco_rms_max+0.5);
  hbw->Sumw2();
  hbw->GetXaxis()->SetTitle("bco_{rms}");

  TH2* hca = new TH2F("hChRmsHits","",chmax+1,-0.5,chmax+0.5,hitmax,0.5,hitmax+0.5);
  hca->GetXaxis()->SetTitle("ch_{width}");
  hca->GetYaxis()->SetTitle("Hits");

  TH2* hba = new TH2F("hBcoRmsHits","",bcomax+1,-0.5,bcomax+0.5,hitmax,0.5,hitmax+0.5);
  hba->GetXaxis()->SetTitle("bco_{width}");
  hba->GetYaxis()->SetTitle("Hits");

  long nentries = t->GetEntries();
  bool bad_channel = false;
  for( long ientry = 0; ientry < nentries; ientry++ ) {
    bad_channel = false;
    t->GetEntry(ientry);
    have->Fill(adc_sum/(float)nhit);
    if( nhit == 1 ) continue;

    for( int i = 0; i < nhit; i++ ) {
      if( ch_id[i] == 21 ) bad_channel = true;
      if( bad_channel ) continue;
      hdedx->Fill(abs(ch_idx[i]),ch_adc[i]);
      hclst->Fill(-1*ch_idx[i]);
      if( bco_rms < 1.0 ) hclst_cut->Fill(-1*ch_idx[i]);
    }
    if( bad_channel ) continue;
    have_cut->Fill(adc_sum/(float)nhit);
    hadc->Fill(adc_sum);
    hca->Fill(ch_w,nhit);
    hba->Fill(bco_w,nhit);
    hcw->Fill(ch_rms/(float)nhit);
    hbw->Fill(bco_w/(float)nhit);
    if( bco_rms < 1.0 ) {
      hadc_cut->Fill(adc_sum);
      hcw_cut->Fill(ch_rms/(float)nhit);
    }
  }

  TCanvas* c1 = new TCanvas("c1","c1",1200,600);
  c1->Divide(4,2);
  c1->cd(1);
  gPad->SetLogy();
  hadc->UseCurrentStyle();
  hadc->Draw();
  hadc_cut->SetMarkerColor(kBlue);
  hadc_cut->SetLineColor(kBlue);
  hadc_cut->Draw("same");

  TLegend* leg = new TLegend(0.4,0.65,0.85,0.85,0,"NDC");
  leg->SetFillStyle(0);
  leg->SetBorderSize(0.0);
  leg->SetTextSize(0.04);
  leg->AddEntry(hadc,"N_{hits} > 1","P");
  leg->AddEntry(hadc_cut,"N_{hits} > 1, same BCO","P");
  leg->Draw();

  c1->cd(2);
  gPad->SetLogy();
  have->UseCurrentStyle();
  have->Draw();
  have_cut->SetMarkerColor(kBlue);
  have_cut->SetLineColor(kBlue);
  have_cut->Draw("same");

  TLegend* leg2 = new TLegend(0.65,0.65,0.95,0.85,0,"NDC");
  leg2->SetFillStyle(0);
  leg2->SetBorderSize(0.0);
  leg2->SetTextSize(0.04);
  leg2->AddEntry(have,"All events","P");
  leg2->AddEntry(have_cut,"N_{hits} > 1","P");
  leg2->Draw();

  c1->cd(3);
  gPad->SetLogy();
  hcw->UseCurrentStyle();
  hcw->Draw();
  hcw_cut->SetMarkerColor(kBlue);
  hcw_cut->SetLineColor(kBlue);
  //hcw_cut->Draw("same");

  c1->cd(4);
  gPad->SetLogy();
  hbw->UseCurrentStyle();
  hbw->Draw();

  c1->cd(5);
  gPad->SetLogz();
  gPad->SetRightMargin(0.12);
  hca->UseCurrentStyle();
  hca->Draw("colz");

  c1->cd(6);
  gPad->SetLogz();
  gPad->SetRightMargin(0.12);
  hba->UseCurrentStyle();
  hba->Draw("colz");

  c1->cd(7);
  gPad->SetLogy();
  hclst->UseCurrentStyle();
  hclst->SetAxisRange(-9.5,19.5,"X");
  hclst->Draw();
  hclst_cut->SetMarkerColor(kBlue);
  hclst_cut->SetLineColor(kBlue);
  //hclst_cut->Draw("same");

  c1->cd(8);
  gPad->SetLogy();
  hdedx->UseCurrentStyle();
  hdedx->Draw();

}
