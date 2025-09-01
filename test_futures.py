"""
Test script for the futures trading system.
"""
from src.jobs.daily_volume_job import DailyVolumeJob
from src.data_feeder.futures_data_feeder import FuturesDataFeeder


def test_volume_analysis():
    """Test the volume analysis functionality."""
    print("🔍 Testing Futures Volume Analysis...")
    
    try:
        # Initialize the volume job
        job = DailyVolumeJob(output_dir="test_volume_data")
        
        print("📊 Running volume analysis...")
        results = job.run_once()
        
        if results:
            print(f"✅ Analysis completed successfully!")
            print(f"   • Total markets: {results.get('total_markets', 0)}")
            print(f"   • Recommended markets: {results.get('recommended_markets', 0)}")
            print(f"   • Exchanges analyzed: {len(results.get('exchanges_analyzed', []))}")
            
            # Show top 5 recommended symbols
            recommended = results.get('recommended_symbols', [])[:5]
            if recommended:
                print(f"   • Top 5 recommended: {', '.join(recommended)}")
            
            return True
        else:
            print("❌ Volume analysis failed")
            return False
            
    except Exception as e:
        print(f"❌ Error in volume analysis: {e}")
        return False


def test_futures_data_feeder():
    """Test the futures data feeder."""
    print("\n📡 Testing Futures Data Feeder...")
    
    try:
        # Initialize data feeder
        feeder = FuturesDataFeeder()
        
        # Test getting volume metrics from Binance (most reliable)
        from src.core.futures_models import ExchangeType
        
        print("Fetching volume metrics from Binance...")
        metrics = feeder.get_24h_volume_metrics(ExchangeType.BINANCE)
        
        if metrics:
            print(f"✅ Fetched {len(metrics)} futures markets from Binance")
            
            # Show top 5 by volume
            top_5 = sorted(metrics, key=lambda x: x.volume_usd_24h, reverse=True)[:5]
            print("   Top 5 by volume:")
            for i, m in enumerate(top_5, 1):
                print(f"   {i}. {m.symbol}: ${m.volume_usd_24h:,.0f}")
            
            return True
        else:
            print("❌ No volume metrics fetched")
            return False
            
    except Exception as e:
        print(f"❌ Error in futures data feeder: {e}")
        return False


def main():
    """Run all tests."""
    print("🚀 Testing Futures Trading System Components\n")
    
    # Test 1: Futures Data Feeder
    test1_passed = test_futures_data_feeder()
    
    # Test 2: Volume Analysis
    test2_passed = test_volume_analysis()
    
    # Summary
    print(f"\n{'='*50}")
    print("TEST SUMMARY")
    print(f"{'='*50}")
    print(f"Futures Data Feeder: {'✅ PASS' if test1_passed else '❌ FAIL'}")
    print(f"Volume Analysis:     {'✅ PASS' if test2_passed else '❌ FAIL'}")
    
    if test1_passed and test2_passed:
        print("\n🎉 All tests passed! The futures system is ready to use.")
    else:
        print("\n⚠️  Some tests failed. Check the error messages above.")


if __name__ == "__main__":
    main()
