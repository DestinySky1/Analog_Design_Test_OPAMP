* Two-stage differential OTA, gm/ID stage design, 180 nm
* @RNL(type="header") { @VERSION("0.4"); @USE-PACKAGE(name="rnl-std-all", version="0.4"); }
.subckt ota ip im op om vdd 0
Iref vdd b 2.077771516e-05
Mref b b 0 0 nch W=14.1u L=0.6u
Mtail t b 0 0 nch W=94.8u L=0.6u
M1 xp ip t 0 nch W=31.7u L=0.6u
M2 xm im t 0 nch W=31.7u L=0.6u
M3 xp a vdd vdd pch W=53.4u L=0.6u
M4 xm a vdd vdd pch W=53.4u L=0.6u
R1 xp a 800k
R2 xm a 800k
C1 xp a 40f
C2 xm a 40f
M5 op xp vdd vdd pch W=108.3u L=0.42u
M6 om xm vdd vdd pch W=108.3u L=0.42u
M7 op s 0 0 nch W=36.8u L=0.9u
M8 om s 0 0 nch W=36.8u L=0.9u
M9 op xp 0 0 nch W=4.1u L=0.75u
M10 om xm 0 0 nch W=4.1u L=0.75u
R3 op s 800k
R4 om s 800k
C3 op s 40f
C4 om s 40f
Rzp xp zp 2810
Rzm xm zm 2810
Ccp zp op 245f
Ccm zm om 245f
* @RNL {
*   &vdd @ADD-TO $SUPPLY_NET_SET;
*   # @SELECT-NET(port=true) => @REMOVE-FROM $PORT_FILL_SET;
*   {#M1 #M2 #M7 #M8 #M9 #M10 #Mref #Mtail} @SET-SYMBOL $NMOS;
*   {#M3 #M4 #M5 #M6} @SET-SYMBOL $PMOS;
*   %bias = {#Iref #Mref} @GROUP;
*   %input_stage = {#M1 #M2 #M3 #M4 #Mtail} @GROUP;
*   %output_stage = {#M5 #M6 #M7 #M8 #M9 #M10} @GROUP;
*   %input_cm = {#R1 #C1 #R2 #C2} @GROUP;
*   %output_cm = {#R3 #C3 #R4 #C4} @GROUP;
*   %compensation = {#Rzp #Ccp #Rzm #Ccm} @GROUP;
*   (-6, 66) @TEXT("Fourth-round OTA", size=2.2, halign="start");
*   (-6, 62.5) @TEXT("180 nm   /   1.1 V nominal   /   W/L in micrometres   /   NMOS bulk = 0, PMOS bulk = vdd", size=1.04, halign="start");
*   (113, 59) @TEXT("Complementary pull-down", size=1.25, halign="middle");
*   (-6, 59) @TEXT("Reference and tail bias", size=1.25, halign="start");
*   (28, 59) @TEXT("Differential input stage", size=1.25, halign="middle");
*   (75.5, 59) @TEXT("Common-source outputs", size=1.25, halign="middle");
*   #Mref @PLACE(-2, 15) => @ORIENT("MY");
*   #Mref::name @PLACE(-8.5, 16);
*   #Mref @TEXT("${w}/${l}", key="wl", size=0.84) => @PLACE(-8.5, 14);
*   #Mtail @PLACE(28, 15) => @ORIENT("R0");
*   #Mtail::name @PLACE(29.3, 16);
*   #Mtail @TEXT("${w}/${l}", key="wl", size=0.84) => @PLACE(29.3, 14);
*   #M1 @PLACE(18, 32) => @ORIENT("R0");
*   #M1::name @PLACE(19.3, 33);
*   #M1 @TEXT("${w}/${l}", key="wl", size=0.84) => @PLACE(19.3, 31);
*   #M2 @PLACE(38, 32) => @ORIENT("MY");
*   #M2::name @PLACE(31.4, 33);
*   #M2 @TEXT("${w}/${l}", key="wl", size=0.84) => @PLACE(31.4, 31);
*   #M3 @PLACE(18, 46) => @ORIENT("MY");
*   #M3::name @PLACE(11.4, 47);
*   #M3 @TEXT("${w}/${l}", key="wl", size=0.84) => @PLACE(11.4, 45);
*   #M4 @PLACE(38, 46) => @ORIENT("R0");
*   #M4::name @PLACE(39.3, 47);
*   #M4 @TEXT("${w}/${l}", key="wl", size=0.84) => @PLACE(39.3, 45);
*   #M5 @PLACE(65, 46) => @ORIENT("R0");
*   #M5::name @PLACE(66.3, 47);
*   #M5 @TEXT("${w}/${l}", key="wl", size=0.84) => @PLACE(66.3, 45);
*   #M6 @PLACE(86, 46) => @ORIENT("R0");
*   #M6::name @PLACE(87.3, 47);
*   #M6 @TEXT("${w}/${l}", key="wl", size=0.84) => @PLACE(87.3, 45);
*   #M7 @PLACE(65, 32) => @ORIENT("MY");
*   #M7::name @PLACE(58, 33);
*   #M7 @TEXT("${w}/${l}", key="wl", size=0.84) => @PLACE(58, 31);
*   #M8 @PLACE(86, 32) => @ORIENT("R0");
*   #M8::name @PLACE(87.3, 33);
*   #M8 @TEXT("${w}/${l}", key="wl", size=0.84) => @PLACE(87.3, 31);
*   #M9 @PLACE(105, 32) => @ORIENT("R0");
*   #M9::name @PLACE(106.3, 33);
*   #M9 @TEXT("${w}/${l}", key="wl", size=0.84) => @PLACE(106.3, 31);
*   #M10 @PLACE(121, 32) => @ORIENT("R0");
*   #M10::name @PLACE(122.3, 33);
*   #M10 @TEXT("${w}/${l}", key="wl", size=0.84) => @PLACE(122.3, 31);
*   #Iref @PLACE(-2, 44) => @ORIENT("R0");
*   %p_vdd = $IO_PORT @ATTACH &vdd => @PLACE(-2, 55.3) => @ORIENT("R270");
*   &vdd @WIRE(mode="straight") {%p_vdd::pin #Iref::p};
*   %rail_input = (28, 53);
*   $JUNCTION @ATTACH %rail_input => @PLACE(28, 53);
*   %supply_input = $SUPPLY @ATTACH &vdd => @PLACE(28, 54.6) => @ORIENT("R0");
*   &vdd @WIRE(mode="straight") {%supply_input::pin %rail_input};
*   &vdd @WIRE(mode="straight") {#M3::s (18, 53) %rail_input};
*   &vdd @WIRE(mode="straight") {%rail_input (38, 53) #M4::s};
*   %rail_output = (75.5, 53);
*   $JUNCTION @ATTACH %rail_output => @PLACE(75.5, 53);
*   %supply_output = $SUPPLY @ATTACH &vdd => @PLACE(75.5, 54.6) => @ORIENT("R0");
*   &vdd @WIRE(mode="straight") {%supply_output::pin %rail_output};
*   &vdd @WIRE(mode="straight") {#M5::s (65, 53) %rail_output};
*   &vdd @WIRE(mode="straight") {%rail_output (86, 53) #M6::s};
*   %p_ground = $IO_PORT @ATTACH &0 => @PLACE(42, 55.3) => @ORIENT("R270");
*   %port_ground_symbol = $GROUND @ATTACH &0 => @PLACE(42, 53.4) => @ORIENT("R0");
*   &0 @WIRE(mode="straight") {%p_ground::pin %port_ground_symbol::pin};
*   %gnd_Mtail = (28, 9);
*   $JUNCTION @ATTACH %gnd_Mtail => @PLACE(28, 9);
*   %gnd_center = (42, 9);
*   $JUNCTION @ATTACH %gnd_center => @PLACE(42, 9);
*   %gnd_M7 = (65, 9);
*   $JUNCTION @ATTACH %gnd_M7 => @PLACE(65, 9);
*   &0 @WIRE(mode="straight") {#Mref::s (-2, 9) %gnd_Mtail};
*   &0 @WIRE(mode="straight") {%gnd_Mtail #Mtail::s};
*   &0 @WIRE(mode="straight") {%gnd_Mtail %gnd_center};
*   %ground_rail = $GROUND @ATTACH &0 => @PLACE(42, 8.0) => @ORIENT("R0");
*   &0 @WIRE(mode="straight") {%gnd_center %ground_rail::pin};
*   &0 @WIRE(mode="straight") {%gnd_center %gnd_M7};
*   &0 @WIRE(mode="straight") {%gnd_M7 #M7::s};
*   &0 @WIRE(mode="straight") {%gnd_M7 (86, 9) #M8::s};
*   %M9_drain = $NET_LABEL @ATTACH &op => @PLACE(103, 39) => @ORIENT("R0");
*   &op @WIRE(mode="straight") {%M9_drain::pin (105, 39) #M9::d};
*   %M9_gate = $NET_LABEL @ATTACH &xp => @PLACE(99, 32) => @ORIENT("R0");
*   &xp @WIRE(mode="straight") {%M9_gate::pin #M9::g};
*   %M9_ground = $GROUND @ATTACH &0 => @PLACE(105, 26) => @ORIENT("R0");
*   &0 @WIRE(mode="straight") {#M9::s %M9_ground::pin};
*   %M10_drain = $NET_LABEL @ATTACH &om => @PLACE(119, 39) => @ORIENT("R0");
*   &om @WIRE(mode="straight") {%M10_drain::pin (121, 39) #M10::d};
*   %M10_gate = $NET_LABEL @ATTACH &xm => @PLACE(115, 32) => @ORIENT("R0");
*   &xm @WIRE(mode="straight") {%M10_gate::pin #M10::g};
*   %M10_ground = $GROUND @ATTACH &0 => @PLACE(121, 26) => @ORIENT("R0");
*   &0 @WIRE(mode="straight") {#M10::s %M10_ground::pin};
*   %bias_drain = (-2, 20);
*   $JUNCTION @ATTACH %bias_drain => @PLACE(-2, 20);
*   %bias_gate = (2.5, 15);
*   $JUNCTION @ATTACH %bias_gate => @PLACE(2.5, 15);
*   &b @WIRE(mode="straight") {#Iref::n %bias_drain};
*   &b @WIRE(mode="straight") {%bias_drain #Mref::d};
*   &b @WIRE(mode="straight") {%bias_drain (2.5, 20) %bias_gate};
*   &b @WIRE(mode="straight") {#Mref::g %bias_gate};
*   &b @WIRE(mode="straight") {%bias_gate #Mtail::g};
*   (13, 15.7) @TEXT("b", size=1.0, halign="start");
*   %tail_sum = (28, 26);
*   $JUNCTION @ATTACH %tail_sum => @PLACE(28, 26);
*   &t @WIRE(mode="straight") {#M1::s (18, 26) %tail_sum};
*   &t @WIRE(mode="straight") {%tail_sum (38, 26) #M2::s};
*   &t @WIRE(mode="straight") {%tail_sum #Mtail::d};
*   (29, 25) @TEXT("t", size=1.0, halign="start");
*   %in_cm_gate = (28, 46);
*   $JUNCTION @ATTACH %in_cm_gate => @PLACE(28, 46);
*   &a @WIRE(mode="straight") {#M3::g %in_cm_gate};
*   &a @WIRE(mode="straight") {%in_cm_gate #M4::g};
*   %gate_a = $NET_LABEL @ATTACH &a => @PLACE(26, 49) => @ORIENT("R0");
*   &a @WIRE(mode="straight") {%in_cm_gate (28, 49) %gate_a::pin};
*   %port_ip = $IO_PORT @ATTACH &ip => @PLACE(8.5, 55.3) => @ORIENT("R270");
*   &ip @WIRE(mode="straight") {%port_ip::pin (8.5, 32) #M1::g};
*   %port_im = $IO_PORT @ATTACH &im => @PLACE(48, 55.3) => @ORIENT("R270");
*   &im @WIRE(mode="straight") {%port_im::pin (48, 32) #M2::g};
*   %node_xp = (18, 39);
*   $JUNCTION @ATTACH %node_xp => @PLACE(18, 39);
*   &xp @WIRE(mode="straight") {#M3::d %node_xp};
*   &xp @WIRE(mode="straight") {%node_xp #M1::d};
*   %tag_xp = $NET_LABEL @ATTACH &xp => @PLACE(13, 39) => @ORIENT("R0");
*   &xp @WIRE(mode="straight") {%node_xp %tag_xp::pin};
*   %node_xm = (38, 39);
*   $JUNCTION @ATTACH %node_xm => @PLACE(38, 39);
*   &xm @WIRE(mode="straight") {#M4::d %node_xm};
*   &xm @WIRE(mode="straight") {%node_xm #M2::d};
*   %tag_xm = $NET_LABEL @ATTACH &xm => @PLACE(43, 39) => @ORIENT("MY");
*   &xm @WIRE(mode="straight") {%node_xm %tag_xm::pin};
*   %node_op = (65, 39);
*   $JUNCTION @ATTACH %node_op => @PLACE(65, 39);
*   &op @WIRE(mode="straight") {#M5::d %node_op};
*   &op @WIRE(mode="straight") {%node_op #M7::d};
*   %tag_op = $IO_PORT @ATTACH &op => @PLACE(70, 39) => @ORIENT("MY");
*   &op @WIRE(mode="straight") {%node_op %tag_op::pin};
*   %node_om = (86, 39);
*   $JUNCTION @ATTACH %node_om => @PLACE(86, 39);
*   &om @WIRE(mode="straight") {#M6::d %node_om};
*   &om @WIRE(mode="straight") {%node_om #M8::d};
*   %tag_om = $IO_PORT @ATTACH &om => @PLACE(91, 39) => @ORIENT("MY");
*   &om @WIRE(mode="straight") {%node_om %tag_om::pin};
*   %M5_drive = $NET_LABEL @ATTACH &xp => @PLACE(60, 46) => @ORIENT("R0");
*   &xp @WIRE(mode="straight") {%M5_drive::pin #M5::g};
*   %M6_drive = $NET_LABEL @ATTACH &xm => @PLACE(80, 46) => @ORIENT("R0");
*   &xm @WIRE(mode="straight") {%M6_drive::pin #M6::g};
*   %out_cm_gate = (76, 32);
*   $JUNCTION @ATTACH %out_cm_gate => @PLACE(76, 32);
*   &s @WIRE(mode="straight") {#M7::g %out_cm_gate};
*   &s @WIRE(mode="straight") {%out_cm_gate #M8::g};
*   %gate_s = $NET_LABEL @ATTACH &s => @PLACE(74, 28) => @ORIENT("R0");
*   &s @WIRE(mode="straight") {%out_cm_gate (76, 28) %gate_s::pin};
*   (-6, 2) @TEXT("Input common-mode sense", size=1.25, halign="start");
*   (35, 2) @TEXT("Output common-mode sense", size=1.25, halign="start");
*   (68, 2) @TEXT("Miller compensation", size=1.25, halign="start");
*   %sense_xp1 = (-5, -7);
*   $JUNCTION @ATTACH %sense_xp1 => @PLACE(-5, -7);
*   %sense_end_10 = $NET_LABEL @ATTACH &xp => @PLACE(-6.5, -7) => @ORIENT("R0");
*   &xp @WIRE(mode="straight") {%sense_xp1 %sense_end_10::pin};
*   %sense_top_1 = (8, -4.5);
*   $JUNCTION @ATTACH %sense_top_1 => @PLACE(8, -4.5);
*   %sense_low_1 = (8, -11);
*   $JUNCTION @ATTACH %sense_low_1 => @PLACE(8, -11);
*   &a @WIRE(mode="straight") {%sense_top_1 %sense_low_1};
*   (8.65, -6.4) @TEXT("a", size=1.0, halign="start");
*   %sense_xm1 = (21, -7);
*   $JUNCTION @ATTACH %sense_xm1 => @PLACE(21, -7);
*   %sense_end_12 = $NET_LABEL @ATTACH &xm => @PLACE(22.5, -7) => @ORIENT("MY");
*   &xm @WIRE(mode="straight") {%sense_xm1 %sense_end_12::pin};
*   #R1 @PLACE(1.5, -4.5) => @ORIENT("R90");
*   &xp @WIRE(mode="straight") {%sense_xp1 (-5, -4.5) #R1::p};
*   &a @WIRE(mode="straight") {#R1::n %sense_top_1};
*   #R1::name @PLACE(-0.5, -3.2);
*   #R1::value @PLACE(-0.5, -6.35);
*   #C1 @PLACE(1.5, -11) => @ORIENT("R90");
*   &xp @WIRE(mode="straight") {%sense_xp1 (-5, -11) #C1::p};
*   &a @WIRE(mode="straight") {#C1::n %sense_low_1};
*   #C1::name @PLACE(-0.5, -9.7);
*   #C1::value @PLACE(-0.5, -12.85);
*   #R2 @PLACE(14.5, -4.5) => @ORIENT("R270");
*   &a @WIRE(mode="straight") {%sense_top_1 #R2::n};
*   &xm @WIRE(mode="straight") {#R2::p (21, -4.5) %sense_xm1};
*   #R2::name @PLACE(12.5, -3.2);
*   #R2::value @PLACE(12.5, -6.35);
*   #C2 @PLACE(14.5, -11) => @ORIENT("R270");
*   &a @WIRE(mode="straight") {%sense_low_1 #C2::n};
*   &xm @WIRE(mode="straight") {#C2::p (21, -11) %sense_xm1};
*   #C2::name @PLACE(12.5, -9.7);
*   #C2::value @PLACE(12.5, -12.85);
*   %sense_op3 = (36, -7);
*   $JUNCTION @ATTACH %sense_op3 => @PLACE(36, -7);
*   %sense_end_30 = $NET_LABEL @ATTACH &op => @PLACE(34.5, -7) => @ORIENT("R0");
*   &op @WIRE(mode="straight") {%sense_op3 %sense_end_30::pin};
*   %sense_top_3 = (49, -4.5);
*   $JUNCTION @ATTACH %sense_top_3 => @PLACE(49, -4.5);
*   %sense_low_3 = (49, -11);
*   $JUNCTION @ATTACH %sense_low_3 => @PLACE(49, -11);
*   &s @WIRE(mode="straight") {%sense_top_3 %sense_low_3};
*   (49.65, -6.4) @TEXT("s", size=1.0, halign="start");
*   %sense_om3 = (62, -7);
*   $JUNCTION @ATTACH %sense_om3 => @PLACE(62, -7);
*   %sense_end_32 = $NET_LABEL @ATTACH &om => @PLACE(63.5, -7) => @ORIENT("MY");
*   &om @WIRE(mode="straight") {%sense_om3 %sense_end_32::pin};
*   #R3 @PLACE(42.5, -4.5) => @ORIENT("R90");
*   &op @WIRE(mode="straight") {%sense_op3 (36, -4.5) #R3::p};
*   &s @WIRE(mode="straight") {#R3::n %sense_top_3};
*   #R3::name @PLACE(40.5, -3.2);
*   #R3::value @PLACE(40.5, -6.35);
*   #C3 @PLACE(42.5, -11) => @ORIENT("R90");
*   &op @WIRE(mode="straight") {%sense_op3 (36, -11) #C3::p};
*   &s @WIRE(mode="straight") {#C3::n %sense_low_3};
*   #C3::name @PLACE(40.5, -9.7);
*   #C3::value @PLACE(40.5, -12.85);
*   #R4 @PLACE(55.5, -4.5) => @ORIENT("R270");
*   &s @WIRE(mode="straight") {%sense_top_3 #R4::n};
*   &om @WIRE(mode="straight") {#R4::p (62, -4.5) %sense_om3};
*   #R4::name @PLACE(53.5, -3.2);
*   #R4::value @PLACE(53.5, -6.35);
*   #C4 @PLACE(55.5, -11) => @ORIENT("R270");
*   &s @WIRE(mode="straight") {%sense_low_3 #C4::n};
*   &om @WIRE(mode="straight") {#C4::p (62, -11) %sense_om3};
*   #C4::name @PLACE(53.5, -9.7);
*   #C4::value @PLACE(53.5, -12.85);
*   (10, 5) @TEXT("xp/xm = 0.518 V  /  63.5 uA per input branch", size=0.96, halign="start");
*   (64, 5) @TEXT("op/om = 0.589 V  /  152.9 uA per pull-up branch", size=0.96, halign="start");
*   #Rzp @PLACE(75, -4.5) => @ORIENT("R90");
*   #Ccp @PLACE(88, -4.5) => @ORIENT("R90");
*   %comp_in_p = $NET_LABEL @ATTACH &xp => @PLACE(70, -4.5) => @ORIENT("R0");
*   &xp @WIRE(mode="straight") {%comp_in_p::pin #Rzp::p};
*   &zp @WIRE(mode="straight") {#Rzp::n #Ccp::p};
*   (80, -3.8) @TEXT("zp", size=0.88, halign="start");
*   %comp_out_p = $NET_LABEL @ATTACH &op => @PLACE(93, -4.5) => @ORIENT("MY");
*   &op @WIRE(mode="straight") {#Ccp::n %comp_out_p::pin};
*   #Rzp::name @PLACE(73, -3.2);
*   #Rzp::value @PLACE(73, -6.35);
*   #Ccp::name @PLACE(86, -3.2);
*   #Ccp::value @PLACE(86, -6.35);
*   #Rzm @PLACE(75, -11) => @ORIENT("R90");
*   #Ccm @PLACE(88, -11) => @ORIENT("R90");
*   %comp_in_m = $NET_LABEL @ATTACH &xm => @PLACE(70, -11) => @ORIENT("R0");
*   &xm @WIRE(mode="straight") {%comp_in_m::pin #Rzm::p};
*   &zm @WIRE(mode="straight") {#Rzm::n #Ccm::p};
*   (80, -10.3) @TEXT("zm", size=0.88, halign="start");
*   %comp_out_m = $NET_LABEL @ATTACH &om => @PLACE(93, -11) => @ORIENT("MY");
*   &om @WIRE(mode="straight") {#Ccm::n %comp_out_m::pin};
*   #Rzm::name @PLACE(73, -9.7);
*   #Rzm::value @PLACE(73, -12.85);
*   #Ccm::name @PLACE(86, -9.7);
*   #Ccm::value @PLACE(86, -12.85);
* }
.ends ota
