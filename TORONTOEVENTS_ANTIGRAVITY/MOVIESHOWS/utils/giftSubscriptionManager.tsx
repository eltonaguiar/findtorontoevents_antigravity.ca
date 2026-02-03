/**
 * UPDATE #109: Gift Subscriptions
 * Send subscriptions as gifts
 */

interface GiftSubscription {
    id: string;
    gifterId: number;
    recipientEmail: string;
    recipientId?: number;
    planId: string;
    duration: number; // months
    message?: string;
    status: 'pending' | 'sent' | 'redeemed' | 'expired';
    createdAt: string;
    sentAt?: string;
    redeemedAt?: string;
    expiresAt: string;
    giftCode: string;
}

class GiftSubscriptionManager {
    private gifts: Map<string, GiftSubscription> = new Map();

    /**
     * Create gift subscription
     */
    createGift(
        gifterId: number,
        recipientEmail: string,
        planId: string,
        duration: number,
        message?: string
    ): GiftSubscription {
        const giftCode = this.generateGiftCode();
        const expiresAt = new Date();
        expiresAt.setFullYear(expiresAt.getFullYear() + 1); // Gift codes expire in 1 year

        const gift: GiftSubscription = {
            id: `gift_${Date.now()}`,
            gifterId,
            recipientEmail,
            planId,
            duration,
            message,
            status: 'pending',
            createdAt: new Date().toISOString(),
            expiresAt: expiresAt.toISOString(),
            giftCode
        };

        this.gifts.set(gift.id, gift);
        return gift;
    }

    /**
     * Send gift (via email)
     */
    async sendGift(giftId: string): Promise<void> {
        const gift = this.gifts.get(giftId);
        if (!gift) throw new Error('Gift not found');

        // In production, send email to recipient
        console.log(`Sending gift to ${gift.recipientEmail}`);

        gift.status = 'sent';
        gift.sentAt = new Date().toISOString();
    }

    /**
     * Redeem gift code
     */
    redeemGift(giftCode: string, userId: number): GiftSubscription {
        const gift = Array.from(this.gifts.values()).find(g => g.giftCode === giftCode);

        if (!gift) {
            throw new Error('Invalid gift code');
        }

        if (gift.status === 'redeemed') {
            throw new Error('Gift code already redeemed');
        }

        if (gift.status === 'expired' || new Date() > new Date(gift.expiresAt)) {
            gift.status = 'expired';
            throw new Error('Gift code has expired');
        }

        gift.status = 'redeemed';
        gift.recipientId = userId;
        gift.redeemedAt = new Date().toISOString();

        return gift;
    }

    /**
     * Validate gift code
     */
    validateGiftCode(giftCode: string): { valid: boolean; error?: string } {
        const gift = Array.from(this.gifts.values()).find(g => g.giftCode === giftCode);

        if (!gift) {
            return { valid: false, error: 'Invalid gift code' };
        }

        if (gift.status === 'redeemed') {
            return { valid: false, error: 'Gift code already redeemed' };
        }

        if (new Date() > new Date(gift.expiresAt)) {
            return { valid: false, error: 'Gift code has expired' };
        }

        return { valid: true };
    }

    /**
     * Get user's sent gifts
     */
    getSentGifts(userId: number): GiftSubscription[] {
        return Array.from(this.gifts.values()).filter(g => g.gifterId === userId);
    }

    /**
     * Generate unique gift code
     */
    private generateGiftCode(): string {
        return `GIFT-${Math.random().toString(36).substr(2, 4).toUpperCase()}-${Math.random().toString(36).substr(2, 4).toUpperCase()}`;
    }
}

export const giftSubscriptionManager = new GiftSubscriptionManager();

/**
 * Gift subscription purchase component
 */
import React, { useState } from 'react';
import { subscriptionManager } from './subscriptionManager';

interface GiftPurchaseProps {
    userId: number;
    onComplete: (gift: GiftSubscription) => void;
}

export function GiftPurchase({ userId, onComplete }: GiftPurchaseProps) {
    const [recipientEmail, setRecipientEmail] = useState('');
    const [selectedPlan, setSelectedPlan] = useState('basic');
    const [duration, setDuration] = useState(1);
    const [message, setMessage] = useState('');
    const [processing, setProcessing] = useState(false);

    const plans = subscriptionManager.getPlans().filter(p => p.tier !== 'free');

    const handlePurchase = async () => {
        setProcessing(true);

        try {
            // Create gift
            const gift = giftSubscriptionManager.createGift(
                userId,
                recipientEmail,
                selectedPlan,
                duration,
                message
            );

            // Send gift email
            await giftSubscriptionManager.sendGift(gift.id);

            onComplete(gift);
        } catch (error) {
            console.error('Gift purchase failed:', error);
        } finally {
            setProcessing(false);
        }
    };

    const selectedPlanDetails = plans.find(p => p.id === selectedPlan);
    const totalPrice = selectedPlanDetails ? selectedPlanDetails.price * duration : 0;

    return (
        <div className="gift-purchase">
            <h2>🎁 Gift a Subscription</h2>
            <p>Give the gift of entertainment</p>

            <div className="form-section">
                <label>Recipient Email</label>
                <input
                    type="email"
                    value={recipientEmail}
                    onChange={(e) => setRecipientEmail(e.target.value)}
                    placeholder="recipient@example.com"
                />
            </div>

            <div className="form-section">
                <label>Select Plan</label>
                <div className="plan-selector">
                    {plans.map(plan => (
                        <button
                            key={plan.id}
                            onClick={() => setSelectedPlan(plan.id)}
                            className={`plan-option ${selectedPlan === plan.id ? 'selected' : ''}`}
                        >
                            <div className="plan-name">{plan.name}</div>
                            <div className="plan-price">${plan.price}/mo</div>
                        </button>
                    ))}
                </div>
            </div>

            <div className="form-section">
                <label>Duration</label>
                <select value={duration} onChange={(e) => setDuration(Number(e.target.value))}>
                    <option value={1}>1 Month</option>
                    <option value={3}>3 Months</option>
                    <option value={6}>6 Months</option>
                    <option value={12}>12 Months</option>
                </select>
            </div>

            <div className="form-section">
                <label>Personal Message (Optional)</label>
                <textarea
                    value={message}
                    onChange={(e) => setMessage(e.target.value)}
                    placeholder="Add a personal message..."
                    rows={4}
                />
            </div>

            <div className="total-section">
                <span>Total:</span>
                <span className="total-price">${totalPrice.toFixed(2)}</span>
            </div>

            <button
                onClick={handlePurchase}
                disabled={!recipientEmail || processing}
                className="purchase-button"
            >
                {processing ? 'Processing...' : 'Purchase Gift'}
            </button>
        </div>
    );
}

/**
 * Gift redemption component
 */
interface GiftRedemptionProps {
    userId: number;
    onRedeem: (gift: GiftSubscription) => void;
}

export function GiftRedemption({ userId, onRedeem }: GiftRedemptionProps) {
    const [giftCode, setGiftCode] = useState('');
    const [error, setError] = useState('');

    const handleRedeem = () => {
        setError('');

        try {
            const gift = giftSubscriptionManager.redeemGift(giftCode, userId);
            onRedeem(gift);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Redemption failed');
        }
    };

    return (
        <div className="gift-redemption">
            <h3>Redeem Gift Code</h3>

            <div className="redemption-input">
                <input
                    type="text"
                    value={giftCode}
                    onChange={(e) => setGiftCode(e.target.value.toUpperCase())}
                    placeholder="GIFT-XXXX-XXXX"
                />
                <button onClick={handleRedeem} disabled={!giftCode}>
                    Redeem
                </button>
            </div>

            {error && <div className="error-message">{error}</div>}
        </div>
    );
}

const styles = `
.gift-purchase {
  max-width: 600px;
  margin: 0 auto;
  padding: 2rem;
}

.gift-purchase h2 {
  margin: 0 0 0.5rem;
  font-size: 2rem;
}

.gift-purchase > p {
  margin: 0 0 2rem;
  opacity: 0.8;
}

.form-section {
  margin-bottom: 1.5rem;
}

.form-section label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 600;
}

.form-section input,
.form-section select,
.form-section textarea {
  width: 100%;
  padding: 0.75rem;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  color: white;
  font-family: inherit;
}

.form-section input:focus,
.form-section select:focus,
.form-section textarea:focus {
  outline: none;
  border-color: #667eea;
}

.plan-selector {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 1rem;
}

.plan-option {
  padding: 1rem;
  background: rgba(0, 0, 0, 0.2);
  border: 2px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  color: white;
  cursor: pointer;
  transition: all 0.2s;
}

.plan-option:hover {
  border-color: rgba(102, 126, 234, 0.5);
}

.plan-option.selected {
  border-color: #667eea;
  background: rgba(102, 126, 234, 0.2);
}

.plan-name {
  font-weight: 600;
  margin-bottom: 0.25rem;
}

.plan-price {
  opacity: 0.8;
  font-size: 0.9rem;
}

.total-section {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 8px;
  margin-bottom: 1.5rem;
  font-size: 1.25rem;
  font-weight: 700;
}

.total-price {
  color: #4ade80;
  font-size: 1.5rem;
}

.purchase-button {
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

.purchase-button:hover:not(:disabled) {
  transform: scale(1.02);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.purchase-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.gift-redemption {
  max-width: 500px;
  margin: 0 auto;
  padding: 2rem;
}

.gift-redemption h3 {
  margin: 0 0 1.5rem;
}

.redemption-input {
  display: flex;
  gap: 0.5rem;
}

.redemption-input input {
  flex: 1;
  padding: 0.75rem;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  color: white;
  font-family: monospace;
  text-transform: uppercase;
}

.redemption-input button {
  padding: 0.75rem 1.5rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
  border-radius: 8px;
  color: white;
  font-weight: 700;
  cursor: pointer;
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
