#include "protocentralAds1292r.h"
#include "ecgRespirationAlgo.h"
#include <SPI.h>
#include <WiFiNINA.h>
#include <WiFiUdp.h>
#include <I2S.h>

// WiFi settings
char ssid[] = "AndroidAP4840";
char pass[] = "afxo0473";
int status = WL_IDLE_STATUS;

// UDP settings
WiFiUDP udp;
char server_ip[] = "192.168.43.21";    // use the IP address of the computer running the Python script
unsigned int server_port = 80;

// Audio settings
const int sample_rate = 8000;
const int channels = 1;
const int bits_per_sample = 32;
const int buffer_size = 256;
int sample = 0;


//LED Status
#define BLUE_LED 10
#define GREEN_LED 9


volatile uint8_t globalHeartRate = 0;
volatile uint8_t globalRespirationRate=0;

//Pin declartion the other you need are controlled by the SPI library
const int ADS1292_DRDY_PIN = 7;
const int ADS1292_CS_PIN = 8;
const int ADS1292_START_PIN = 6;
const int ADS1292_PWDN_PIN = 5;

#define CES_CMDIF_PKT_START_1   0x0A
#define CES_CMDIF_PKT_START_2   0xFA
#define CES_CMDIF_TYPE_DATA     0x02
#define CES_CMDIF_PKT_STOP      0x0B
#define DATA_LEN                13
#define ZERO                    0

volatile char DataPacket[DATA_LEN];
const char DataPacketFooter[2] = {ZERO, CES_CMDIF_PKT_STOP};
const char DataPacketHeader[5] = {CES_CMDIF_PKT_START_1, CES_CMDIF_PKT_START_2, DATA_LEN, ZERO, CES_CMDIF_TYPE_DATA};

int16_t ecgWaveBuff, ecgFilterout;
int16_t resWaveBuff,respFilterout;

ads1292r ADS1292R;
ecg_respiration_algorithm ECG_RESPIRATION_ALGORITHM;



void setup() {
  // start serial communication
  Serial.begin(9600);
  //ECG Initiation
  delay(2000);

  SPI.begin();
  SPI.setBitOrder(MSBFIRST);
  //CPOL = 0, CPHA = 1
  SPI.setDataMode(SPI_MODE1);
  // Selecting 1Mhz clock for SPI
  SPI.setClockDivider(SPI_CLOCK_DIV16);

  pinMode(ADS1292_DRDY_PIN, INPUT);
  pinMode(ADS1292_CS_PIN, OUTPUT);
  pinMode(ADS1292_START_PIN, OUTPUT);
  pinMode(ADS1292_PWDN_PIN, OUTPUT);
  ADS1292R.ads1292Init(ADS1292_CS_PIN,ADS1292_PWDN_PIN,ADS1292_START_PIN);

  
   if (!I2S.begin(I2S_RIGHT_JUSTIFIED_MODE, 8000, 32)) {
    Serial.println("Failed to initialize I2S!");
    while (1); // do nothing
  }
  // attempt to connect to WiFi network
  while (status != WL_CONNECTED) {
    Serial.print("Attempting to connect to SSID: ");
    Serial.println(ssid);
    status = WiFi.begin(ssid, pass);
    LED(0,1);
    delay(2500);
    LED(0,0);
    delay(2500);
  }
  LED(0,1);
  udp.begin(server_port);
  Serial.println("Connected to WiFi network");
}

void loop() {
  
  

  // create a buffer for the audio data
  int audio_data[buffer_size+16];
  int ecg[16];
  // fill the buffer with audio data
  for (int i = 0; i < buffer_size; i++) {
    sample = I2S.read();
    while(sample ==0){
      sample = I2S.read();
    }
    audio_data[i] = sample;   // read a 32-bit sample from the ADC
    
    if (i%16==0){
      ads1292OutputValues ecgRespirationValues;
      boolean ret = ADS1292R.getAds1292EcgAndRespirationSamples(ADS1292_DRDY_PIN,ADS1292_CS_PIN,&ecgRespirationValues);
      if (ret == true) 
          {
            ecgWaveBuff = (int16_t)(ecgRespirationValues.sDaqVals[1] >> 8) ;  // ignore the lower 8 bits out of 24bits
//            resWaveBuff = (int16_t)(ecgRespirationValues.sresultTempResp>>8) ;
        
            if(ecgRespirationValues.leadoffDetected == false)
            {
              ECG_RESPIRATION_ALGORITHM.ECG_ProcessCurrSample(&ecgWaveBuff, &ecgFilterout);   // filter out the line noise @40Hz cutoff 161 order
              ECG_RESPIRATION_ALGORITHM.QRS_Algorithm_Interface(ecgFilterout,&globalHeartRate); // calculate
//              respFilterout = ECG_RESPIRATION_ALGORITHM.Resp_ProcessCurrSample(resWaveBuff);
//              ECG_RESPIRATION_ALGORITHM.RESP_Algorithm_Interface(respFilterout,&globalRespirationRate);
        
            }else{
              ecgFilterout = 0;
//              respFilterout = 0;
            }
          }
          ecg[i/16] = ecgFilterout;
    }
  }
  
   for (int i = 0; i <16; i++) {
    audio_data[buffer_size+i] = ecg[i];
 }
  
  // send the audio data over UDP
  udp.beginPacket(server_ip, server_port);
  udp.write((uint8_t*)audio_data,( buffer_size+16) * sizeof(int));
  udp.endPacket();
  
  // wait for the next sample period
  delay(1000 / sample_rate);
}



void LED (int LED, int Status){
  if(LED==0){
    if(Status==0){
      digitalWrite(BLUE_LED,LOW);
    }
    if(Status==1){
      digitalWrite(BLUE_LED,HIGH);
    }
  }
  if(LED==1){
    if(Status==0){
      digitalWrite(GREEN_LED,LOW);
    }
    if(Status==1){
      digitalWrite(GREEN_LED,HIGH);
    }
  }
}
