import express from 'express';
// import cors from 'cors';
import 'dotenv/config';
import { presignedUpload } from './handlers/uploadHandler';

const app= express();
const PORT= process.env.PORT || 3000;

// app.use(cors());
app.use(express.json());

// Routes
app.get('/', (req, res) => {
  res.json({ message: 'Bank Statement Analysis Backend' });
});

app.post('/api/uploads/presign', presignedUpload);

app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});