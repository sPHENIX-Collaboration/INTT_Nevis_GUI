#!/usr/bin/perl

#  A test FVTX Graphic User Interface with Perl, has changed to Python as developing language.
#  Author: Zhengyun You

use Tk;
use Tk::BrowseEntry;
use Time::Local;

$option = 1;
foreach $arg ( @ARGV ){
    if ( $arg eq "-fvtx" ){
        $option = 2;
    }
    elsif ( $arg eq "-ldrd" ) {
        $option = 1;
    }
}

$data_mode = 1;

$mw_x = 800;
$mw_y = 1000;

$smalltextfg = '#00CCFF';
$smalltextbg = '#333366';

$slinebg = '#cccc00';
$slinetext = 'hello';

$bigfont = "9x15bold";
$normalfont = "6x13";

if ( $option == 1 ) {
    print "Opening LDRD configure...\n";
    $n_sector  = 20;
    $n_column  = 1;
    @n_module = ( 8, 8, 8, 8 );
}
elsif ( $option == 2 ) {
    print "Opening FVTX configure...\n";
    $n_sector  = 48;
    $n_column  = 2;
    @n_module = ( 5, 13, 13, 13 );
}

$n_station = 4;
$n_register = 32;
@register_name = ( " ",      "lbp1", "lbp2",   "lbb",      "lff",        "Vref",    "Vfb2",   "Vth0",
                   "Vth1",   "Vth2", "Vth3",   "Vth4",     "Vth5",       "Vth6",    "Vth7",   "AqBCO",
                   "Alines", "Kill", "Inject", "SendData", "RejectHits", "WildReg", "Mod256", "SPR",
                   "SPR",    "SPR",  "SPR",    "SPR",      "SCR",        "SCR",     "SCR",    "SCR" );
@register_default = ( 0, 100, 74, 29, 13, 202, 172, 8,    8, 8, 8, 8, 8, 8, 8, 0,
                      0, 0, 0, 0, 1, 0, 1, 0,             0, 0, 0, 0, 0, 0, 0, 0 );
$n_register_display = 10;
@register_display_no = ( 5, 6, 7, 8, 9, 10, 11, 12, 13, 14 );

$instr_id = "001";
$check_id = "000";

$mw = MainWindow->new( -width=>$mw_x, -height=>$mw_y );
$mw->title("FVTX GUI");

$cur_y = 0;
$time_f_y = 50;
$time_f = $mw->Frame( -background=>'grey' )->place( -anchor=>'nw', -x=>'0', -y=>$cur_y, -width=>$mw_x, -height=>$time_f_y );
$cur_y += $time_f_y;
$time_l = $time_f->Label( -background=>$smalltextbg, -fg=>$smalltextfg, -font =>$normalfont)->pack();

$station_label_y = 50;
$station_label_f = $mw->Frame( -background=>'yellow' )->place( -anchor=>'nw', -x=>'0', -y=>$cur_y, -width=>$mw_x, -height=>$station_label_y );
$cur_y += $station_label_y;
for ( my( $i_station ) = 0; $i_station < $n_station; $i_station++ ) {
    my( $station_name ) = "Station $i_station";
    my( $station_x ) = 0.2*$i_station + 0.15;
    $station_l[$i_station] = $station_label_f->Label( -text=>$station_name )->place( -relx=>$station_x, -rely=>0.3 );
}

$sector_f_y = $n_sector*18;
$sector_f = $mw->Frame()->place( -anchor=>'nw', -x=>'0', -y=>$cur_y, -width=>$mw_x, -height=>$sector_f_y );
$cur_y += $sector_f_y;
for ( my( $i_station ) = 0; $i_station < $n_station; $i_station++ ) {
    for ( my( $i_sector ) = 0; $i_sector < $n_sector; $i_sector++ ) {
            my( $sector_x ) = 0.2*$i_station + 0.08*($i_sector-$i_sector%($n_sector/2))/($n_sector/2) + 0.1;
            my( $sector_y ) = (1.9/$n_sector)*($i_sector%($n_sector/2)) + 0.05;
            my( $sector_name ) = "$i_sector";

            $sector_b[$i_station][$i_sector] = $sector_f->Button( -text=>$sector_name, 
                                                                  -command=>[ \&open_sector, $i_station, $i_sector ], 
                                                                  -width=>'5', -height=>'1', -bg=>'green' );
            printf ( "$sector_x    $sector_y \n" );
            $sector_b[$i_station][$i_sector]->place( -relx=>$sector_x, -rely=>$sector_y ); 
    }
}

$control_f_y = 100;
$control_f = $mw->Frame( -background=>'grey' )->place( -anchor=>'nw', -x=>'0', -y=>$cur_y, -width=>$mw_x, -height=>$control_f_y );
$cur_y += $control_f_y;
for ( my ( $i_station ) = 0; $i_station < $n_station; $i_station++ ) {
    $read_station_b = $control_f->Button( -text=>'read', -command=>[ \&read_station_dialog, $i_station ],  
                                          -width=>'5', -height=>'1', -bg=>'green' );
    $read_station_x = 0.2*$i_station + 0.15;
    $read_station_b->place( -relx=>$read_station_x, -rely=>'0.2' );
}

for ( my ( $i_station ) = 0; $i_station < $n_station; $i_station++ ) {
    $write_station_b = $control_f->Button( -text=>'write', -command=>[ \&write_station_dialog, $i_station ],
                                           -width=>'5', -height=>'1', -bg=>'green' );
    $write_station_x = 0.2*$i_station + 0.15;
    $write_station_b->place( -relx=>$write_station_x, -rely=>'0.6' );
}

$status_y = 100;
$status_t = $mw->Text( -background=>'blue', -font =>$bigfont)->place( -anchor=>'nw', -x=>'0', -y=>$cur_y, -width=>$mw_x, -height=>$status_y );
$cur_y += $status_y;
$mw->configure( -height=>$cur_y );

$exit_b = $mw->Button( -text=>'exit',-command=>sub{exit}, -bg=>"green", -activebackground=>"green" )->place( -relx=>0.925, -rely=>0.01);

@file_data = ( "data_station0.txt", "data_station1.txt", "data_station2.txt", "data_station3.txt" );
@file_data_new = ( "data_station0_new.txt", "data_station1_new.txt", "data_station2_new.txt", "data_station3_new.txt" );
for ( my ( $i_station ) = 0; $i_station < $n_station; $i_station++ ) {
    &read_station( $i_station );
}

$mw->repeat( 1000, \&update );

MainLoop;

sub update
{

  $dtime = `date`;
  chop $dtime;
  $time_l->configure( -text=>$dtime );

}

sub read_from_file {
  local ($filevar) = @_;

  <$filevar>;
}

sub write_station_dialog
{
    my( $i_station ) = @_;
    my( $default_name ) = $file_data_new[$i_station];
    my( @types ) = ( ["Config Files", '.txt', 'TEXT'],  ["All Files", "*"] );

    my( $save_file ) = $mw->getSaveFile( -filetypes => \@types,
        -initialfile=>$default_name,
        -defaultextension => '.txt');
    unless ( $save_file ) { return; }

    open ( $cur_file, ">$save_file" ) || die( "Can't open $save_file \n" );
    for ( my( $i_sector ) = 0; $i_sector < $n_sector; $i_sector++ ) {
        &write_sector( $i_station, $i_sector );
        printf STDOUT ( "station $i_station sector $i_sector written.\n" );
    }
    printf STDOUT ( "station $i_station written.\n" );
}

sub write_station
{
    my ( $i_station ) = @_;
    open ( $cur_file, ">$file_data_new[$i_station]" );

    #&test_dec_to_bin;

    for ( my( $i_sector ) = 0; $i_sector < $n_sector; $i_sector++ ) {
        &write_sector( $i_station, $i_sector );
        printf STDOUT ( "station $i_station sector $i_sector written.\n" );
    }
    printf STDOUT ( "station $i_station written.\n" );
}

sub write_station_default
{
    my ( $i_station ) = @_;
    $write_default = 1;
    open ( $cur_file, ">$file_data[$i_station]" );

    #&test_dec_to_bin;

    for ( my( $i_sector ) = 0; $i_sector < $n_sector; $i_sector++ ) {
        &write_sector( $i_station, $i_sector );
        printf STDOUT ( "station $i_station sector $i_sector written.\n" );
    }
    printf STDOUT ( "station $i_station written.\n" );
    $write_default = 0;
}

sub read_station_dialog
{
    my( $i_station ) = @_;
    my( $default_name ) = $file_data[$i_station];
    my( @types ) = ( ["Config Files", '.txt', 'TEXT'],  ["All Files", "*"] );

    my( $open_file ) = $mw->getOpenFile( -filetypes => \@types,
        -initialfile=>$default_name,
        -defaultextension => '.txt');
    unless ( $open_file ) { return; }

    open ( $cur_file, $open_file ) || die( "Can't open $open_file \n" ); 
    for ( my( $i_sector ) = 0; $i_sector < $n_sector; $i_sector++ ) {
        &read_sector( $i_station, $i_sector );
        printf STDOUT ( "station $i_station sector $i_sector read.\n" );
    }
    printf STDOUT ( "station $i_station read.\n" );
}

sub read_station
{
    my( $i_station ) = @_;
    unless ( open ( $cur_file, "$file_data[$i_station]" ) ) {
        &write_station_default( $i_station );
    }

    open ( $cur_file, "$file_data[$i_station]" ) || die( "Can't open $file_data[$i_station]" ) ;
    #while ($line = &read_from_file($cur_file)) {
    #    printf STDOUT ( "$line" );
    #}

    for ( my( $i_sector ) = 0; $i_sector < $n_sector; $i_sector++ ) {
        &read_sector( $i_station, $i_sector );
        printf STDOUT ( "station $i_station sector $i_sector read.\n" );
    }
    printf STDOUT ( "station $i_station read.\n" );
}

sub read_station_temp
{
    my( $i_station ) = @_;
    open ( $cur_file, "$file_data[$i_station]" ) || die( "Can't open $file_data[$i_station]" ) ;

    for ( my $i_sector = 0; $i_sector < $n_sector; $i_sector++ ) {
        for ( my $i_column = 0; $i_column < $n_column; $i_column++ ) {
            for ( my $i_module = 0; $i_module < $n_module[$i_station]; $i_module++ ) {
                for ( my $i_register = 0; $i_register < $n_register; $i_register++ ) {
                    read( $cur_file, $line, 25 );            # use read to read designated number of chars;
                    $fpix_data_temp[$i_station][$i_sector][$i_column][$i_module][$i_register] = $line;
                    #printf STDOUT ( "$i_station $i_sector $i_column $i_module $i_register = $fpix_data_temp[$i_station][$i_sector][$i_column][$i_module][$i_register] \n" );
                }
            }
        }
    }
    printf STDOUT ( "station $i_station read.\n" );
}

sub write_sector
{
    my( $i_station, $i_sector ) = @_;
    #printf ( "called $i_station, $i_sector, $n_column, $n_module[$i_station] \n" );
    for ( my( $i_column ) = 0; $i_column < $n_column; $i_column++ ) {
        for ( my( $i_module ) = 0; $i_module < $n_module[$i_station]; $i_module++ ) {
             &write_module( $i_station, $i_sector, $i_column, $i_module );
             #printf STDOUT ( "station $i_station sector $i_sector column $i_column module $i_module written \n" );
        }
    }
}

sub read_sector
{
    my( $i_station, $i_sector ) = @_;
    for ( my( $i_column ) = 0; $i_column < $n_column; $i_column++ ) {
        for ( my( $i_module ) = 0; $i_module < $n_module[$i_station]; $i_module++ ) {
             &read_module( $i_station, $i_sector, $i_column, $i_module );
             #printf STDOUT ( "station $i_station sector $i_sector column $i_column module $i_module written \n" );
        }
    }
}

sub write_module
{
    my( $i_station, $i_sector, $i_column, $i_module ) = @_;

    if ( $data_mode == 1) {
        my( $head ) = &dec_to_bin( 255, 8 );
        my( $length ) = &dec_to_bin( 56, 16 );
        my( $location_station ) = &dec_to_bin( $i_station, 2 );
        my( $location_sector ) = &dec_to_bin( $i_sector, 6 );
        my( $location ) = "$location_station$location_sector";
        my( $instr ) = "00000010"; #write
        my( $address ) = &dec_to_bin( 0, 24 );
        my( $tail ) = &dec_to_bin( 255, 8 );

        for ( my( $i_register ) = 0; $i_register < $n_register; $i_register++ ) {
            my( $fpix ) = substr( $fpix_data[$i_station][$i_sector][$i_column][$i_module][$i_register], 0, 24);

            if ( $write_default == 1 ) {
                my( $column_id ) = &dec_to_bin( $i_column, 1 );
                my( $module_id ) = &dec_to_bin( $i_module, 4 );
                my( $chip_id ) = "${column_id}${module_id}";
                my( $register_id ) = &dec_to_bin( $i_register, 5 );
                my( $data_id ) = &dec_to_bin( $register_default[$i_register], 8 );
                #printf STDOUT ( "$register_default[$i_register] = $data_id\n" );
                $fpix = "$chip_id$register_id$instr_id$data_id$check_id";
            } 
            my( $eprom_data ) = "$head$length$location$instr$address$fpix$tail";
            printf $cur_file ( "$eprom_data\n" );
        }
    }
}

sub read_module
{
    my( $i_station, $i_sector, $i_column, $i_module ) = @_;

    for ( my( $i_register ) = 0; $i_register < $n_register; $i_register++ ) {
        $line = &read_from_file($cur_file);     # use read_from_file to read in a whole line;
        #read( $cur_file, $line, 25 );           # use read to read designated number of chars;
        #printf STDOUT ( "$i_station $i_sector $i_column $i_module $i_register = $line \n" );
   
        my( $length ) = &bin_to_dec( substr( $line, 8, 16 ), 16 );
        $data_mode = 2;
        if ( $length == 56 ) { $data_mode = 1; }
        #printf STDOUT ( "data_mode = $data_mode\n" );

        $fpix_data[$i_station][$i_sector][$i_column][$i_module][$i_register] = substr( $line, 64, 24 );
    }
}

sub dec_to_bin
{
    my( $num, $n_bit ) = @_;
    my( $str ) = "";
    if( $num >= 2**$n_bit ) { printf STDERR ( "dec_to_bin error: input number $num > $n_bit bit range \n" ); }

    for( my( $i_bit ) = 0; $i_bit < $n_bit; $i_bit++ ) {
        $str = "${str}0";
    }

    my( $i_bit ) = 0;
    while( $num != 0 ) {
        $mod = $num % 2;
        $num = ($num - $mod) / 2;
        substr( $str, $n_bit-$i_bit-1, 1 )= $mod;
        $i_bit++;
    }

    #printf STDOUT ( "$str\n" );
    return $str;
}

sub test_dec_to_bin
{
    for ( my( $i_test ) = 0; $i_test < 33; $i_test++ ) { 
        $test_str = &dec_to_bin( $i_test, 5 ); 
        printf STDOUT ( "$i_test = $test_str\n" );
    }
}

sub bin_to_dec
{
    my( $str, $n_bit ) = @_;
    my( $num ) = 0;

    for ( my($i_bit) = 0; $i_bit < $n_bit; $i_bit++ ) {
        $cur_bit = substr($str, $n_bit-$i_bit-1, 1);
        $num += $cur_bit * ( 2**($i_bit) );
    }

    return $num;
}

sub open_sector
{
    my( $i_station, $i_sector ) = @_;
    printf STDOUT ( "$i_station $i_sector $n_module[$i_station]\n");

    if( exists( $window_sector[$i_station][$i_sector]) ) {
        printf STDOUT ( "window_sector[$i_station][$i_sector] exists \n");
        $window_sector[$i_station][$i_sector]->raise;  #->grab;
        $window_sector[$i_station][$i_sector]->focus;
        return;
    }
    
    $window_sector[$i_station][$i_sector] = $mw->Toplevel( -width=>'1000', -height=>'400' );
    $window_sector[$i_station][$i_sector]->title("station_${i_station}_sector_${i_sector}");

    for ( my( $i_column ) = 0; $i_column < $n_column; $i_column++ ) {
        for ( my( $i_module ) = 0; $i_module < $n_module[$i_station]; $i_module++ ) {
            $name_module = "module $i_module";
            $module_x = 0.05 + 0.07*$i_module;
            $module_y = 0.2 + 0.3*$i_column;

            $button_module[$i_column][$i_module] = $window_sector[$i_station][$i_sector]->Button( -text=>$name_module,
                                                                                                  -command=>[ \&open_module, $i_station, $i_sector, $i_column, $i_module ],
                                                                                                  -width=>'5', -height=>'1' );
            $button_module[$i_column][$i_module]->place( -relx=>$module_x, -rely=>$module_y );
        }
    }

    $window_sector[$i_station][$i_sector]->update;
}

sub open_module
{
    my( $i_station, $i_sector, $i_column, $i_module ) = @_;
    printf STDOUT ( "$i_station $i_sector $i_column $i_module \n" );

    if( exists( $window_module[$i_station][$i_sector][$i_column][$i_module] ) ) {
        printf STDOUT ( "window_module[$i_station][$i_sector][$i_column][$i_module] exists \n" );
        return;
    }

    $window_module[$i_station][$i_sector][$i_column][$i_module] = $window_sector[$i_station][$i_sector]->Toplevel( -width=>'1000', -height=>'700' );
    $window_module[$i_station][$i_sector][$i_column][$i_module]->title("station_${i_station}_sector_${i_sector}_column_${i_column}_module_${i_module}");

    my( $frame_height ) = 600;
    my( $frame_register_no ) = $window_module[$i_station][$i_sector][$i_column][$i_module]->Frame( -background=>'green' )->place( -anchor=>'nw', -x=>'0', -y=>'0', -width=>'100', -height=>$frame_height );
    my( $frame_register_name ) = $window_module[$i_station][$i_sector][$i_column][$i_module]->Frame( -background=>'blue' )->place( -anchor=>'nw', -x=>'100', -y=>'0', -width=>'100', -height=>$frame_height );
    my( $frame_db_value ) = $window_module[$i_station][$i_sector][$i_column][$i_module]->Frame( -background=>'red'  )->place( -anchor=>'nw', -x=>'200', -y=>'0', -width=>'100', -height=>$frame_height );
    my( $frame_IO_box ) = $window_module[$i_station][$i_sector][$i_column][$i_module]->Frame( -background=>'yellow'  )->place( -anchor=>'nw', -x=>'300', -y=>'0', -width=>'100', -height=>$frame_height );
    my( $frame_read ) = $window_module[$i_station][$i_sector][$i_column][$i_module]->Frame( -background=>'pink'  )->place( -anchor=>'nw', -x=>'400', -y=>'0', -width=>'100', -height=>$frame_height );
    my( $frame_write ) = $window_module[$i_station][$i_sector][$i_column][$i_module]->Frame( -background=>'orange'  )->place( -anchor=>'nw', -x=>'500', -y=>'0', -width=>'100', -height=>$frame_height );

    for ( my( $i_register_display ) = 0; $i_register_display < $n_register_display; $i_register_display++ ) {
        my( $i_register ) = $register_display_no[$i_register_display];
        #printf STDOUT ( "i_register = $i_register \n" );
        $register_no_str = "REG$i_register";
        $label_y = 0.05+0.9/$n_register_display*$i_register_display;
        $label_register_no = $frame_register_no->Label( -text=>$register_no_str )->place( -relx=>0.3, -rely=>$label_y );

        $label_register_name = $frame_register_name->Label( -text=>$register_name[$i_register] )->place( -relx=>0.3, -rely=>$label_y );

        $label_db_value = $frame_db_value->Label( -text=>&get_data_id( ${fpix_data[$i_station][$i_sector][$i_column][$i_module][$i_register]} ) )->place( -relx=>0.3, -rely=>$label_y );

        $new_value[$i_station][$i_sector][$i_column][$i_module][$i_register] = &get_data_id( ${fpix_data[$i_station][$i_sector][$i_column][$i_module][$i_register]} );
        $entry_IO_box[$i_station][$i_sector][$i_column][$i_module][$i_register] = $frame_IO_box->Entry( -textvariable=>\$new_value[$i_station][$i_sector][$i_column][$i_module][$i_register] )->place( -relx=>0.0, -rely=>$label_y );
#        $entry_IO_box[$i_register]->bind( "<Return>", sub{ printf "lala $newvalue[$i_register] xx $i_station xx $i_sector xx $i_column xx $i_module xx \$i_register xx $fpix_data[$i_station][$i_sector][$i_column][$i_module][$i_register]\n"; $label_db_value->configure( -text=>&get_data_id( ${fpix_data[$i_station][$i_sector][$i_column][$i_module][$i_register]} ) ) } );

        $button_read_data = $frame_read->Button( -text=>'read', -command=>[ \&read_data, $i_station, $i_sector, $i_column, $i_module, $i_register ] )->place( -relx=>0.3, -rely=>$label_y );
        $button_write_data = $frame_write->Button( -text=>'write', -command=>[ \&write_data, $i_station, $i_sector, $i_column, $i_module, $i_register ] )->place( -relx=>0.3, -rely=>$label_y );
    }
    
    #my($frame_register_name) = $window_module_a->Frame()->place( -anchor=>'nw', -x=>'100', -y=>'0', -width=>'200', -height=>$frame_height );


    #$button_read = $window_module_a->Button( -text=>'Read', -command=>[ \&read_data, $i_station, $i_sector, $i_column, $i_module ], -width=>'5', -height=>'1' );
    #$button_read->place( -relx=>'0.5', -rely=>'0.3' );

    #$button_write = $window_module_a->Button( -text=>'Write', -command=>[ \&write_data, $i_station, $i_sector, $i_column, $i_module ], -width=>'5', -height=>'1' );
    #$button_write->place( -relx=>'0.5', -rely=>'0.6' );

    $window_module[$i_station][$i_sector][$i_column][$i_module]->update;
}

sub read_data
{
    my( $i_station, $i_sector, $i_column, $i_module, $i_register ) = @_;
    #printf STDOUT ( "i_station = $i_station \n");
    &read_station_temp( $i_station );
    printf( "$i_station $i_sector $i_column $i_module $i_register , $fpix_data_temp[$i_station][$i_sector][$i_column][$i_module][$i_register] \n" );
    $fpix_data[$i_station][$i_sector][$i_column][$i_module][$i_register] = $fpix_data_temp[$i_station][$i_sector][$i_column][$i_module][$i_register];
    $new_value[$i_station][$i_sector][$i_column][$i_module][$i_register] = &get_data_id( $fpix_data[$i_station][$i_sector][$i_column][$i_module][$i_register] );
}

sub write_data
{
    my( $i_station, $i_sector, $i_column, $i_module, $i_register ) = @_;
    printf( "$i_station $i_sector $i_column $i_module $i_register , $new_value[$i_station][$i_sector][$i_column][$i_module][$i_register], ${fpix_data[$i_station][$i_sector][$i_column][$i_module][$i_register]} \n" );
    &set_data_id( $i_station, $i_sector, $i_column, $i_module, $i_register );
    printf( "$i_station $i_sector $i_column $i_module $i_register , $new_value[$i_station][$i_sector][$i_column][$i_module][$i_register], ${fpix_data[$i_station][$i_sector][$i_column][$i_module][$i_register]} \n" );
    &write_station( $i_station );
}

sub get_chip_id
{
    my( $fpix_data_str ) = @_;
    return &bin_to_dec( substr( $fpix_data_str, 0, 5 ), 5 );
}

sub get_register_id
{
    my( $fpix_data_str ) = @_;
    return &bin_to_dec( substr( $fpix_data_str, 5, 5 ), 5 );
}

sub get_data_id
{
    my( $fpix_data_str ) = @_;
    return &bin_to_dec( substr( $fpix_data_str, 13, 8 ), 8 );
}

sub set_data_id
{
    my( $i_station, $i_sector, $i_column, $i_module, $i_register ) = @_;
    substr( $fpix_data[$i_station][$i_sector][$i_column][$i_module][$i_register], 13, 8 ) = &dec_to_bin($new_value[$i_station][$i_sector][$i_column][$i_module][$i_register], 8);
}


#sub read_data
#{
#    my( $i_station, $i_sector, $i_column, $i_module ) = @_;
#
#    for( my( $i_register ) = 0; $i_register < $n_register; $i_register++ ) {
#        $fpix_data_str = ${fpix_data[$i_station][$i_sector][$i_column][$i_module][$i_register]};
#        #printf STDOUT ( "$i_station $i_sector $i_column $i_module $i_register = $fpix_data_str\n" );
#        $chip_id     = substr( $fpix_data_str, 0, 5 );
#        $register_id = substr( $fpix_data_str, 5, 5 );
#        $data_id     = substr( $fpix_data_str, 13, 8 );
#
#        $register_id_dec = &bin_to_dec( $register_id, 5 );
#        $data_id_dec = &bin_to_dec( $data_id, 8 );
#        printf STDOUT ( "$register_id = $register_id_dec, $data_id = $data_id_dec, $register_name[$i_register] \n" );
#    }
#}

#sub write_data
#{
#    my( $i_station, $i_sector, $i_column, $i_module ) = @_;
#    &write_station( $i_station );  
#}
