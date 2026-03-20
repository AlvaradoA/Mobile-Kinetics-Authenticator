import React, { useState, useEffect, useRef } from 'react';
import { StyleSheet, Text, View, Switch, Modal, TouchableOpacity } from 'react-native';
import { Accelerometer, Gyroscope } from 'expo-sensors';

// INGEST OUTPUT URL (from TF outputs):
const INGEST_API_URL = "INGEET_API_URL";
// VERIFY OUTPUT URL (from TF outputs):
const VERIFY_API_URL = "VERIFY_API_URL";

export default function App() {
  const [isHarvesting, setIsHarvesting] = useState(false);
  const [isShieldActive, setIsShieldActive] = useState(false);
  const [isLocked, setIsLocked] = useState(false);
  const [harvestCount, setHarvestCount] = useState(0);

  // Use a ref to prevent spamming the AWS API while waiting for a response
  const isVerifyingRef = useRef(false);

  useEffect(() => {
    // 50ms interval = 20 readings per second (Perfect for a 0.25s snatch window)
    Accelerometer.setUpdateInterval(50);
    Gyroscope.setUpdateInterval(50);

    let currentAccel = { x: 0, y: 0, z: 0 };
    let currentGyro = { x: 0, y: 0, z: 0 };

    const accelSub = Accelerometer.addListener(data => { currentAccel = data; });
    const gyroSub = Gyroscope.addListener(data => { currentGyro = data; });

    let rollingBuffer = [];
    let harvestBatch = [];
    
    const timer = setInterval(() => {
      const reading = {
        ax: currentAccel.x, ay: currentAccel.y, az: currentAccel.z,
        gx: currentGyro.x, gy: currentGyro.y, gz: currentGyro.z
      };

      // ---------------------------------------------------------
      // 1. HARVEST MODE (Collects a steady stream of training data)
      // ---------------------------------------------------------
      if (isHarvesting) {
        harvestBatch.push(reading);
        if (harvestBatch.length >= 50) {
          sendHarvestData([...harvestBatch]);
          harvestBatch = [];
        }
      }

      // ---------------------------------------------------------
      // 2. ACTIVE SHIELD MODE (0.25s Event-Driven Inference)
      // ---------------------------------------------------------
      if (isShieldActive && !isVerifyingRef.current) {
        // Keep a rolling window of the last 5 readings (0.25 seconds of context)
        rollingBuffer.push(reading);
        if (rollingBuffer.length > 5) rollingBuffer.shift();

        // Calculate total G-Force Magnitude (Resting gravity is exactly 1.0G)
        const gForce = Math.sqrt(
          Math.pow(reading.ax, 2) + 
          Math.pow(reading.ay, 2) + 
          Math.pow(reading.az, 2)
        );

        // Calculate the "Jerk" (How far from resting gravity is it?)
        const jerk = Math.abs(gForce - 1.0);

        // TRIGGER: Trigger ML verification on slight sudden movement (> 0.2 Gs)
        if (jerk > 0.2 && rollingBuffer.length === 5) {
          console.log(`⚡ SNATCH DETECTED in 0.25s: ${jerk.toFixed(2)}G. Verifying...`);
          
          isVerifyingRef.current = true; // Lock API to prevent spam
          verifyBiometrics([...rollingBuffer]);
          
          // Cooldown: Ignore other jerks for 2 seconds while AWS decides
          setTimeout(() => {
            isVerifyingRef.current = false;
            rollingBuffer = []; // Clear buffer to reset the window
          }, 2000);
        }
      }
    }, 50);

    return () => {
      accelSub.remove();
      gyroSub.remove();
      clearInterval(timer);
    };
  }, [isHarvesting, isShieldActive]);

  const sendHarvestData = async (dataBatch) => {
    try {
      await fetch(INGEST_API_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ batch: dataBatch })
      });
      setHarvestCount(prev => prev + dataBatch.length);
    } catch (e) { 
      console.error("Harvesting Error", e); 
    }
  };

  const verifyBiometrics = async (buffer) => {
    const size = buffer.length;
    // Average the 0.25s window into a single feature vector for the ML model
    const avg = buffer.reduce((acc, val) => {
      acc.ax += val.ax / size; acc.ay += val.ay / size; acc.az += val.az / size;
      acc.gx += val.gx / size; acc.gy += val.gy / size; acc.gz += val.gz / size;
      return acc;
    }, { ax: 0, ay: 0, az: 0, gx: 0, gy: 0, gz: 0 });

    const featureVector = `${avg.ax},${avg.ay},${avg.az},${avg.gx},${avg.gy},${avg.gz}`;

    try {
      const res = await fetch(VERIFY_API_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ features: featureVector })
      });
      const data = await res.json();
      console.log(`🧠 ML Score: ${data.anomaly_score} | Status: ${data.status}`);
      
      if (data.status === 'LOCKED') {
          setIsLocked(true);
          setIsShieldActive(false); 
      }
    } catch (e) { 
      console.error("Verification Error", e); 
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Mobile Kinetics Authenticator</Text>
      
      <View style={styles.card}>
        <View style={styles.row}>
          <Text style={styles.label}>1. Harvest Training Data</Text>
          <Switch value={isHarvesting} onValueChange={(val) => { setIsHarvesting(val); setIsShieldActive(false); }} />
        </View>
        {isHarvesting && <Text style={styles.subText}>Data Points Sent: {harvestCount}</Text>}
      </View>

      <View style={styles.card}>
        <View style={styles.row}>
          <Text style={styles.label}>2. Active Shield Mode</Text>
          <Switch value={isShieldActive} onValueChange={(val) => { setIsShieldActive(val); setIsHarvesting(false); }} />
        </View>
      </View>

      <Modal visible={isLocked} animationType="slide">
        <View style={styles.lockScreen}>
          <Text style={styles.lockText}>⚠️ UNAUTHORIZED USER</Text>
          <Text style={styles.lockSubText}>Unrecognized behavioral signature.</Text>
          <TouchableOpacity style={styles.button} onPress={() => setIsLocked(false)}>
            <Text style={styles.buttonText}>Verify Identity</Text>
          </TouchableOpacity>
        </View>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, justifyContent: 'center', padding: 20, backgroundColor: '#f4f4f5' },
  title: { fontSize: 26, fontWeight: 'bold', marginBottom: 40, textAlign: 'center' },
  card: { backgroundColor: 'white', padding: 20, borderRadius: 10, marginBottom: 20 },
  row: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  label: { fontSize: 16, fontWeight: '600' },
  subText: { marginTop: 10, color: '#666', fontStyle: 'italic' },
  lockScreen: { flex: 1, backgroundColor: '#991b1b', justifyContent: 'center', alignItems: 'center', padding: 20 },
  lockText: { color: 'white', fontSize: 28, fontWeight: 'bold', textAlign: 'center', marginBottom: 10 },
  lockSubText: { color: '#fca5a5', fontSize: 16, textAlign: 'center', marginBottom: 40 },
  button: { backgroundColor: 'white', padding: 15, borderRadius: 8 },
  buttonText: { color: '#991b1b', fontWeight: 'bold', fontSize: 16 }
});