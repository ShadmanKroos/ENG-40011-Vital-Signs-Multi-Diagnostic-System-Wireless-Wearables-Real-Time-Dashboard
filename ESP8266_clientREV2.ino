#include <ESP8266WiFi.h>
#include <espnow.h>
#include <Wire.h>
#include "MAX30105.h"           //MAX3010x library
#include "heartRate.h"          //Heart rate  calculating algorithm

// Pin Definitions
const int pressureSensorPin = A0;  // Analog pin connected to the pressure sensor
const int ledPin = LED_BUILTIN;    // Built-in LED pin (usually GPIO2 or D4)
const int threshold = 300;         // Pressure threshold to turn on LED (adjust as needed)

// Must match the sender structure
typedef struct struct_message { 
  int temperature;
} struct_message;

// Create a struct_message called myData
struct_message incomingData;
// Create a WiFi client object
WiFiClient client;
float temperature = 0;             // Simulated temperature data
float pressure = 0;
float heartRate = 0;

MAX30105 particleSensor;

const byte RATE_SIZE  = 4; //Increase this for more averaging. 4 is good.
byte rates[RATE_SIZE]; //Array  of heart rates
byte rateSpot = 0;
long lastBeat = 0; //Time at which the last  beat occurred
float beatsPerMinute;
int beatAvg;
int sendDataInterval = 1000;
long lastSend = 0;

long lastMillis = 0;


// Callback function that will be executed when data is received
void OnDataRecv(uint8_t*  mac, uint8_t* incomingDataBytes, uint8_t len) {
  memcpy(&incomingData, incomingDataBytes, sizeof(incomingData));
  Serial.print("Temp: ");
  Serial.println(incomingData.temperature);
  //temperature = incomingData.temperature;
}

// Replace with your network credentials
const char* ssid     = "ShamsKroos";
const char* password = "abcdefgh";

// Server IP and port
//const char* server_ip = "192.168.196.225";  // Replace with your server's IP
const char* server_ip = "172.20.10.4";  // Replace with your server's IP
const uint16_t server_port = 8081;
void sendDataToServer(float temperature, float pressure, float hr) { //send data as binary encoded data
  if (client.connected()){

    // Send temperature
    client.write((uint8_t*)&temperature, sizeof(temperature));
    
    // Send pressure
    client.write((uint8_t*)&pressure, sizeof(pressure));

    //send heart rate
    client.write((uint8_t*)&hr, sizeof(hr));
    
    Serial.print("Temperature: ");
    Serial.print(temperature);
  
    Serial.print(", Pressure: ");
    Serial.print(pressure);
  
    Serial.print(", Heart Rate: ");
    Serial.println(hr);
  }
  
}


float readHR(){
  long irValue = particleSensor.getIR();    //Reading the IR value it will permit us to know if there's a finger on the  sensor or not
                                           //Also detecting a heartbeat
                                           
  if(irValue  > 7000){                                           //If a finger is detected
                    
    //Serial.println(beatAvg);  
      
    if (checkForBeat(irValue) == true)                        //If  a heart beat is detected
    {
      
                                        //Deactivate the buzzer  to have the effect of a "bip"
      //We sensed a beat!
      long delta = millis()  - lastBeat;                   //Measure duration between two beats
      lastBeat  = millis();

      beatsPerMinute = 60 / (delta / 1000.0);           //Calculating  the BPM

      if (beatsPerMinute < 255 && beatsPerMinute > 20)               //To  calculate the average we strore some values (4) then do some math to calculate the  average
      {
        rates[rateSpot++] = (byte)beatsPerMinute; //Store this  reading in the array
        rateSpot %= RATE_SIZE; //Wrap variable

        //Take  average of readings
        beatAvg = 0;
        for (byte x = 0 ; x < RATE_SIZE  ; x++)
          beatAvg += rates[x];
        beatAvg /= RATE_SIZE;
      }
    }
    
  }
  if (irValue < 7000){       //If no finger is detected it inform  the user and put the average BPM to 0 or it will be stored for the next measure
    beatAvg=0;
  }
  return beatAvg;
}

int readPressure(){
   // Read the analog value from the pressure sensor
  int sensorValue = analogRead(pressureSensorPin);

  return sensorValue;
}

int readTemp(){

  return temperature;
}

void connectToServer() {
  // Attempt to connect to the server
  if (client.connect(server_ip, server_port)) {
    Serial.println("Connected to server");
  } else {
    Serial.println("Connection failed. Retrying...");
  }
}

void checkConnection() {
  if (!client.connected()) {
    Serial.println("Disconnected from server, attempting to reconnect...");
      
      // Keep attempting to reconnect until connection is established
      while (!client.connected()) {
        connectToServer();
        delay(5000);  // Wait 5 seconds before attempting to reconnect again
      }
      
    Serial.println("Reconnected to server.");
  }
}
 
void setup() {
  // Initialize Serial Monitor
  Serial.begin(115200);
  //pressure sensor
    // Initialize the built-in LED pin as an output
  //pinMode(ledPin, OUTPUT);
  
  // Turn off the built-in LED (Note: the built-in LED is active-low, so HIGH turns it off)
  digitalWrite(ledPin, HIGH);

  //esp SETUP
  // Set device as a Wi-Fi Station
  WiFi.mode(WIFI_STA);

  // Init ESP-NOW
  if (esp_now_init() != 0) {
    Serial.println("Error initializing ESP-NOW");
    return;
  }
  
  // Once ESPNow is successfully Init, we will register for recv CB to
  // get recv packer info
  esp_now_set_self_role(ESP_NOW_ROLE_SLAVE);
  esp_now_register_recv_cb(OnDataRecv);


  //--------------
  
  // Connect to WiFi
  Serial.print("Connecting to ");
  Serial.println(ssid);
  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected");

  // Try to connect to the server
  connectToServer();
    //  Initialize sensor
  particleSensor.begin(Wire, I2C_SPEED_FAST); //Use default  I2C port, 400kHz speed
  particleSensor.setup(); //Configure sensor with default  settings
  particleSensor.setPulseAmplitudeRed(0x0A); //Turn Red LED to low to  indicate sensor is running
}

void loop() {

  // Check if the client is disconnected
  checkConnection();
  //temprature = Rtemperature;
  pressure = readPressure();
  heartRate = readHR();
  temperature = readTemp();
  // Now that the connection is established, periodically send data
  if (millis()-lastSend > sendDataInterval){
    sendDataToServer(temperature,pressure,heartRate);
    temperature = random(20, 31);
    lastSend = millis();
  }
  // Check for incoming data from the server
  if (client.available()) {
    String serverResponse = client.readStringUntil('\n');
    Serial.println("Server response: " + serverResponse);
  }

   delay(1);
}

  // Check if the sensor value exceeds the threshold
  /*if (sensorValue > threshold) {
    // If pressure is detected (sensor value is higher than the threshold), turn the LED on
    digitalWrite(ledPin, LOW); // Built-in LED is active-low, so LOW turns it on
  } else {
    // If pressure is not detected, turn the LED off
    digitalWrite(ledPin, HIGH); // HIGH turns off the built-in LED
  }*/
