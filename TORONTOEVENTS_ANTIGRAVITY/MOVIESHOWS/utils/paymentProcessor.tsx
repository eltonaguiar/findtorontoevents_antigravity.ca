/**
 * UPDATE #103: Payment Integration
 * Payment processing integration
 */

interface PaymentMethod {
    id: string;
    type: 'card' | 'paypal' | 'apple_pay' | 'google_pay';
    last4?: string;
    brand?: string;
    expiryMonth?: number;
    expiryYear?: number;
    isDefault: boolean;
}

interface PaymentIntent {
    id: string;
    amount: number;
    currency: string;
    status: 'pending' | 'processing' | 'succeeded' | 'failed';
    clientSecret?: string;
}

class PaymentProcessor {
    private apiKey: string = '';

    /**
     * Initialize payment processor
     */
    initialize(apiKey: string): void {
        this.apiKey = apiKey;
    }

    /**
     * Create payment intent
     */
    async createPaymentIntent(amount: number, currency: string = 'usd'): Promise<PaymentIntent> {
        // In production, this would call Stripe/PayPal API
        console.log(`Creating payment intent for ${amount} ${currency}`);

        return {
            id: `pi_${Date.now()}`,
            amount,
            currency,
            status: 'pending',
            clientSecret: `secret_${Date.now()}`
        };
    }

    /**
     * Process payment
     */
    async processPayment(
        paymentMethodId: string,
        amount: number,
        currency: string = 'usd'
    ): Promise<PaymentIntent> {
        // In production, this would call payment gateway
        console.log(`Processing payment: ${amount} ${currency} with method ${paymentMethodId}`);

        // Simulate processing
        await new Promise(resolve => setTimeout(resolve, 2000));

        return {
            id: `pi_${Date.now()}`,
            amount,
            currency,
            status: 'succeeded'
        };
    }

    /**
     * Add payment method
     */
    async addPaymentMethod(userId: number, method: Omit<PaymentMethod, 'id'>): Promise<PaymentMethod> {
        // In production, this would call payment gateway
        console.log(`Adding payment method for user ${userId}`);

        return {
            id: `pm_${Date.now()}`,
            ...method
        };
    }

    /**
     * Get payment methods
     */
    async getPaymentMethods(userId: number): Promise<PaymentMethod[]> {
        // In production, this would fetch from database
        return [];
    }

    /**
     * Remove payment method
     */
    async removePaymentMethod(methodId: string): Promise<void> {
        console.log(`Removing payment method ${methodId}`);
    }

    /**
     * Set default payment method
     */
    async setDefaultPaymentMethod(userId: number, methodId: string): Promise<void> {
        console.log(`Setting default payment method ${methodId} for user ${userId}`);
    }

    /**
     * Refund payment
     */
    async refundPayment(paymentIntentId: string, amount?: number): Promise<void> {
        console.log(`Refunding payment ${paymentIntentId}${amount ? ` amount: ${amount}` : ''}`);
    }

    /**
     * Get payment history
     */
    async getPaymentHistory(userId: number): Promise<PaymentIntent[]> {
        // In production, this would fetch from database
        return [];
    }
}

export const paymentProcessor = new PaymentProcessor();

/**
 * React hook for payments
 */
import { useState } from 'react';

export function usePayment() {
    const [processing, setProcessing] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const processPayment = async (
        paymentMethodId: string,
        amount: number,
        currency: string = 'usd'
    ): Promise<PaymentIntent | null> => {
        setProcessing(true);
        setError(null);

        try {
            const result = await paymentProcessor.processPayment(paymentMethodId, amount, currency);
            return result;
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Payment failed');
            return null;
        } finally {
            setProcessing(false);
        }
    };

    return {
        processing,
        error,
        processPayment
    };
}

/**
 * Payment form component
 */
import React from 'react';

interface PaymentFormProps {
    amount: number;
    onSuccess: (paymentIntent: PaymentIntent) => void;
    onError: (error: string) => void;
}

export function PaymentForm({ amount, onSuccess, onError }: PaymentFormProps) {
    const { processing, error, processPayment } = usePayment();
    const [cardNumber, setCardNumber] = useState('');
    const [expiry, setExpiry] = useState('');
    const [cvc, setCvc] = useState('');

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        // Validate card details
        if (!cardNumber || !expiry || !cvc) {
            onError('Please fill in all fields');
            return;
        }

        // In production, tokenize card with Stripe/PayPal
        const paymentMethodId = 'pm_test';

        const result = await processPayment(paymentMethodId, amount);

        if (result && result.status === 'succeeded') {
            onSuccess(result);
        } else {
            onError(error || 'Payment failed');
        }
    };

    return (
        <form onSubmit={handleSubmit} className="payment-form">
            <div className="form-group">
                <label>Card Number</label>
                <input
                    type="text"
                    value={cardNumber}
                    onChange={(e) => setCardNumber(e.target.value)}
                    placeholder="1234 5678 9012 3456"
                    maxLength={19}
                    disabled={processing}
                />
            </div>

            <div className="form-row">
                <div className="form-group">
                    <label>Expiry</label>
                    <input
                        type="text"
                        value={expiry}
                        onChange={(e) => setExpiry(e.target.value)}
                        placeholder="MM/YY"
                        maxLength={5}
                        disabled={processing}
                    />
                </div>

                <div className="form-group">
                    <label>CVC</label>
                    <input
                        type="text"
                        value={cvc}
                        onChange={(e) => setCvc(e.target.value)}
                        placeholder="123"
                        maxLength={4}
                        disabled={processing}
                    />
                </div>
            </div>

            <button type="submit" disabled={processing} className="submit-button">
                {processing ? 'Processing...' : `Pay $${amount.toFixed(2)}`}
            </button>

            {error && <div className="error-message">{error}</div>}
        </form>
    );
}

const styles = `
.payment-form {
  max-width: 400px;
  margin: 0 auto;
}

.form-group {
  margin-bottom: 1.5rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 600;
}

.form-group input {
  width: 100%;
  padding: 0.75rem;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  color: white;
  font-size: 1rem;
}

.form-group input:focus {
  outline: none;
  border-color: #667eea;
}

.form-row {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 1rem;
}

.submit-button {
  width: 100%;
  padding: 1rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
  border-radius: 8px;
  color: white;
  font-weight: 700;
  font-size: 1rem;
  cursor: pointer;
  transition: all 0.2s;
}

.submit-button:hover:not(:disabled) {
  transform: scale(1.02);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.submit-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.error-message {
  margin-top: 1rem;
  padding: 0.75rem;
  background: rgba(248, 113, 113, 0.1);
  border: 1px solid rgba(248, 113, 113, 0.3);
  border-radius: 6px;
  color: #f87171;
}
`;
