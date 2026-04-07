# Multi-Modal Financial Ledger System - Project Plan

## 1. Project Overview
The Financial Ledger is an advanced, multi-modal AI system designed to automate personal expense tracking. Using a natural, conversational interface via WhatsApp, the project will process unstructured inputs ranging from text messages, speech (voice notes), and images (receipts), parsing them into structured financial data.

## 2. Core Architecture & Workflow

### User Interface: WhatsApp + Twilio
- Interactions take place naturally on WhatsApp.
- **Twilio** acts as the bridge (Sandbox/Webhook), forwarding text, audio, and images to our local Python server (FastAPI & Ngrok).

### Onboarding Flow
- When a user initiates their first chat, the system will prompt them to outline all their available payment methods (e.g., Cash, SBI Debit Card, HDFC Credit Card). 
- This list is saved to the user's profile and ensures the system can accurately assign and track multi-source payment modes for future transactions.

### Multi-Modal Intake & Extraction
- **Audio/Speech (Voice Notes):** 
  - **Tool:** OpenAI Whisper (Local) translates the audio into English text.
  - **Pre-processing:** Librosa is used to normalize audio and filter noise.
- **Images (Receipts):** 
  - **Tool:** PaddleOCR to extract text and bounding boxes.
  - **Pre-processing:** OpenCV handles image pre-processing (deskewing, grayscaling).
  - A custom coordinate sorting algorithm organizes text to match items, prices, and totals on the receipt accurately.
- **Text Messages:** Processed directly via the custom NLP pipeline.

### Custom NLP & Intent Classification Layer
- **Dataset:** We will source an English/financial dataset from a platform like **Kaggle** to train our custom classifier, saving time over building a Hinglish dataset from scratch.
- **Intent & Category Classification:** 
  - Standard categories include: `Food`, `Travel`, `Investment`, `Shopping`, `Salary`/Income, etc.
- **Entity Extraction (NER):** 
  - Maps numerical values (**Amount**), the subject of the transaction (**Vendor/Item**), and the **Payment Mode** used.
  - *Example Flow:* User says, "Spent 200 rupees for filling up petrol on my bike." The NLP layer determines: Amount = `200`, Vendor/Item = `petrol/bike`, Category = `Travel`. If no specific mode is mentioned, it tracks under a default or specified payment mode (e.g., `Cash`).

## 3. Database Strategy
- **Primary Database:** **NeonDB (Serverless PostgreSQL)** will be used to centralize all user transactions and account configurations.
- **Image Handling:** Images sent by the user will be converted into BLOB objects and stored directly within NeonDB rows alongside the transaction record.

## 4. Dataset Generation (English & Hinglish)
To accurately train our custom NLP model, the dataset requires exactly three target outputs for every transaction:
1. `text`: The raw text (e.g. "Flipkart shopping using credit card").
2. `category`: The designated grouping (e.g., `Shopping`).
3. `payment_method`: The stated or default method of payment (e.g., `Credit Card`).

### The Challenge
A raw English dataset (from Kaggle) lacks the nuance of an Indian user's conversational inputs. For instance, a user might use "Hinglish": *"amazon pe 500 ka shopping kharch kiya cash se"*. 

### Our Dataset Augmentation Strategy
1. **Template-Based Generation**: We will systematically expand an English dataset with "Hinglish" templates using code arrays.
   - *Example Template:* `[Merchant] pe [Amount] ka [Category] kharcha kiya payment by [Method]`
   - By feeding randomized lists of merchants, amounts (in numbers and words like "sau", "hazaar"), and methods into the template, we can synthetically create thousands of rows mapping perfectly to the `category` and `payment_method` columns.
2. **Intentional Spelling Robustness**: Hinglish isn't standardized. People spell phonetically. We will programmatically inject variations/typos (e.g. `kharcha`, `karch`, `karcha`, `rupaye`, `rs`, `rs.`) to prevent our NLP layer from being brittle.
3. **Conversational LLM Expansion**: We will utilize an LLM (like GPT/Claude) offline solely to generate diverse paragraph-style transaction transcripts that simulate rambly Whisper audio translations (e.g., *"Aaj subhe gaya tha, petrol bhara 200 ka UPI se"*).

## 5. Analytics & Reporting
- The system fundamentally functions as a personal finance tracker, constantly updating internal balances based on categorizations:
  - **Added:** Money coming into the bank/wallet.
  - **Spent:** Money extracted across any configured payment mode.
  - **Invested:** Allocated funds categorized as investments.
- Users can request a comprehensive **Expense Report** within WhatsApp, surfacing the latest overall balances and aggregated category spending metrics directly from NeonDB.
